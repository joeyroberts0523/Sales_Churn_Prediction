"""
Feature engineering module for LTL Freight Churn Prediction.

Creates features from operational data including:
- Transit/delivery features (on-time, late, days late)
- Pickup features (missed, cancelled, not ready)
- Claims features (count, rate, amounts)
- Revenue and activity features
- Service center features

Source data:
- TransitReview_V03: On-time/late delivery metrics
- FMP030 (Pickups): Pickup completion/cancellation
- Claims Data: Claims filed against shipments
- FRP001: Shipment data
- TOP006: Customer/revenue data
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Union

from ..utils.config import get_config
from ..utils.logging import get_logger

logger = get_logger(__name__)


def create_tenure_features(
    customers_df: pd.DataFrame,
    shipments_df: pd.DataFrame,
    reference_date: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Create tenure-related features from customer and shipment data.
    
    Features created:
    - tenure_days: Days since first shipment
    - tenure_months: Months since first shipment
    - tenure_bucket: Categorical tenure bucket
    
    Args:
        customers_df: Customer master data with customer_code
        shipments_df: Shipment data with customer_code, pickup_date
        reference_date: Date to calculate tenure from
        
    Returns:
        DataFrame with customer_code and tenure features
    """
    if reference_date is None:
        reference_date = datetime.now()
    
    df = customers_df[["customer_code"]].copy()
    
    # Calculate first shipment date from shipments
    if len(shipments_df) > 0 and "pickup_date" in shipments_df.columns:
        shipments_df = shipments_df.copy()
        shipments_df["pickup_date"] = pd.to_datetime(shipments_df["pickup_date"])
        
        first_shipment = shipments_df.groupby("customer_code")["pickup_date"].min().reset_index()
        first_shipment.columns = ["customer_code", "first_shipment_date"]
        
        df = df.merge(first_shipment, on="customer_code", how="left")
        
        # Tenure in days
        df["tenure_days"] = (reference_date - df["first_shipment_date"]).dt.days
        df["tenure_days"] = df["tenure_days"].clip(lower=0).fillna(0)
        
        # Tenure in months
        df["tenure_months"] = (df["tenure_days"] / 30.44).astype(int)
        
        # Tenure bucket
        df["tenure_bucket"] = pd.cut(
            df["tenure_months"],
            bins=[-1, 3, 6, 12, 24, float('inf')],
            labels=["0-3mo", "3-6mo", "6-12mo", "1-2yr", "2yr+"]
        )
        
        df = df.drop(columns=["first_shipment_date"])
    else:
        logger.warning("No shipment data available, setting tenure to 0")
        df["tenure_days"] = 0
        df["tenure_months"] = 0
        df["tenure_bucket"] = "unknown"
    
    logger.info(f"Created tenure features for {len(df)} customers")
    return df


def create_shipment_features(
    shipments_df: pd.DataFrame,
    customer_codes: Optional[List[str]] = None,
    reference_date: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Create shipment activity features with rolling windows.
    
    Features created:
    - shipment_count_30d/60d/90d: Shipment counts by window
    - days_since_last_shipment: Recency
    - revenue_30d/60d/90d: Revenue by window
    - revenue_trend: Revenue change (recent vs prior period)
    - avg_revenue_per_shipment: Average revenue per shipment
    
    Args:
        shipments_df: Shipment data from FRP001
        customer_codes: List of customer codes to process (all if None)
        reference_date: Reference date for calculations
        
    Returns:
        DataFrame with customer_code and shipment features
    """
    if reference_date is None:
        reference_date = datetime.now()
    
    shipments_df = shipments_df.copy()
    shipments_df["pickup_date"] = pd.to_datetime(shipments_df["pickup_date"])
    
    if customer_codes is not None:
        shipments_df = shipments_df[shipments_df["customer_code"].isin(customer_codes)]
    
    # Define time windows
    cutoff_30d = reference_date - timedelta(days=30)
    cutoff_60d = reference_date - timedelta(days=60)
    cutoff_90d = reference_date - timedelta(days=90)
    
    # Initialize result with all unique customers
    all_customers = shipments_df["customer_code"].unique()
    df = pd.DataFrame({"customer_code": all_customers})
    
    # Shipment counts by window
    for days, cutoff in [(30, cutoff_30d), (60, cutoff_60d), (90, cutoff_90d)]:
        recent = shipments_df[shipments_df["pickup_date"] >= cutoff]
        counts = recent.groupby("customer_code").size().reset_index(name=f"shipment_count_{days}d")
        df = df.merge(counts, on="customer_code", how="left")
        df[f"shipment_count_{days}d"] = df[f"shipment_count_{days}d"].fillna(0).astype(int)
    
    # Days since last shipment
    last_shipment = shipments_df.groupby("customer_code")["pickup_date"].max().reset_index()
    last_shipment.columns = ["customer_code", "last_shipment_date"]
    last_shipment["days_since_last_shipment"] = (
        reference_date - last_shipment["last_shipment_date"]
    ).dt.days
    df = df.merge(last_shipment[["customer_code", "days_since_last_shipment"]], 
                  on="customer_code", how="left")
    df["days_since_last_shipment"] = df["days_since_last_shipment"].fillna(9999).astype(int)
    
    # Revenue by window (if revenue column exists)
    if "revenue" in shipments_df.columns:
        for days, cutoff in [(30, cutoff_30d), (60, cutoff_60d), (90, cutoff_90d)]:
            recent = shipments_df[shipments_df["pickup_date"] >= cutoff]
            rev = recent.groupby("customer_code")["revenue"].sum().reset_index(name=f"revenue_{days}d")
            df = df.merge(rev, on="customer_code", how="left")
            df[f"revenue_{days}d"] = df[f"revenue_{days}d"].fillna(0)
        
        # Revenue trend (last 30d vs 30-60d ago)
        recent_30 = shipments_df[(shipments_df["pickup_date"] >= cutoff_30d) & 
                                  (shipments_df["pickup_date"] < reference_date)]
        prev_30 = shipments_df[(shipments_df["pickup_date"] >= cutoff_60d) & 
                               (shipments_df["pickup_date"] < cutoff_30d)]
        
        recent_rev = recent_30.groupby("customer_code")["revenue"].sum().reset_index(name="recent_rev")
        prev_rev = prev_30.groupby("customer_code")["revenue"].sum().reset_index(name="prev_rev")
        
        trend = df[["customer_code"]].merge(recent_rev, on="customer_code", how="left")
        trend = trend.merge(prev_rev, on="customer_code", how="left")
        trend["recent_rev"] = trend["recent_rev"].fillna(0)
        trend["prev_rev"] = trend["prev_rev"].fillna(0)
        
        # Revenue trend ratio (with smoothing)
        trend["revenue_trend"] = (trend["recent_rev"] + 1) / (trend["prev_rev"] + 1) - 1
        df = df.merge(trend[["customer_code", "revenue_trend"]], on="customer_code", how="left")
        df["revenue_trend"] = df["revenue_trend"].fillna(0)
        
        # Average revenue per shipment (90d)
        if df["shipment_count_90d"].sum() > 0:
            df["avg_revenue_per_shipment"] = df["revenue_90d"] / df["shipment_count_90d"].replace(0, 1)
        else:
            df["avg_revenue_per_shipment"] = 0
    
    logger.info(f"Created shipment features for {len(df)} customers")
    return df


def create_transit_features(
    transit_df: pd.DataFrame,
    customer_codes: Optional[List[str]] = None,
    reference_date: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Create transit/delivery features from TransitReview data.
    
    On-time/late logic (direct shipments only):
    - Promise date = APT_DATE if exists, else EST_DELIVERY_DATE
    - On-time = DLV_DATE <= Promise date
    - Late = DLV_DATE > Promise date
    - Days late = DLV_DATE - Promise date (if positive)
    
    Features created:
    - late_delivery_count_90d: Late deliveries in 90 days
    - on_time_count_90d: On-time deliveries in 90 days
    - late_delivery_rate: % shipments late
    - on_time_delivery_rate: % shipments on-time
    - avg_days_late_90d: Average days late (when late)
    - transit_overrun_count: Shipments with transit overrun
    - bring_back_count: Total bring-backs
    - transit_failure_count: Shipments with transit failures
    - misroute_count: Misrouted shipments
    
    Args:
        transit_df: Transit review data from TransitReview_V03
        customer_codes: List of customer codes to process
        reference_date: Reference date for calculations
        
    Returns:
        DataFrame with customer_code and transit features
    """
    if reference_date is None:
        reference_date = datetime.now()
    
    transit_df = transit_df.copy()
    
    # Parse dates
    for col in ["dlv_date", "apt_date", "est_delivery_date", "pu_date"]:
        if col in transit_df.columns:
            transit_df[col] = pd.to_datetime(transit_df[col], errors="coerce")
    
    # Filter to 90-day window
    cutoff_90d = reference_date - timedelta(days=90)
    transit_df = transit_df[transit_df["dlv_date"] >= cutoff_90d]
    
    if customer_codes is not None:
        # Join via agreement or shipper_code depending on available fields
        if "customer_code" in transit_df.columns:
            transit_df = transit_df[transit_df["customer_code"].isin(customer_codes)]
        elif "shipper_code" in transit_df.columns:
            transit_df = transit_df[transit_df["shipper_code"].isin(customer_codes)]
    
    # Calculate on-time/late for direct shipments
    # Direct = no interline carrier (FROM_CARRIER and TO_CARRIER are empty)
    if "from_carrier" in transit_df.columns and "to_carrier" in transit_df.columns:
        transit_df["is_direct"] = (
            (transit_df["from_carrier"].fillna("") == "") & 
            (transit_df["to_carrier"].fillna("") == "")
        )
    else:
        transit_df["is_direct"] = True
    
    # Promise date = APT_DATE if set, else EST_DELIVERY_DATE
    transit_df["promise_date"] = transit_df["apt_date"].fillna(transit_df["est_delivery_date"])
    
    # Calculate late flag and days late
    transit_df["is_late"] = (
        transit_df["is_direct"] & 
        (transit_df["dlv_date"] > transit_df["promise_date"])
    )
    transit_df["days_late"] = np.where(
        transit_df["is_late"],
        (transit_df["dlv_date"] - transit_df["promise_date"]).dt.days,
        0
    )
    
    transit_df["is_on_time"] = (
        transit_df["is_direct"] & 
        (transit_df["dlv_date"] <= transit_df["promise_date"])
    )
    
    # Determine customer grouping column
    group_col = "customer_code"
    if group_col not in transit_df.columns:
        group_col = "shipper_code" if "shipper_code" in transit_df.columns else "agreement_number"
    
    if group_col not in transit_df.columns:
        logger.warning("No customer grouping column found in transit data")
        return pd.DataFrame(columns=["customer_code"])
    
    # Aggregate by customer
    agg_dict = {
        "is_late": "sum",
        "is_on_time": "sum",
        "days_late": ["sum", "mean"],
        "is_direct": "sum",  # Total direct shipments
    }
    
    # Add optional columns
    if "transit_days_overrun" in transit_df.columns:
        transit_df["has_overrun"] = transit_df["transit_days_overrun"].fillna(0) > 0
        agg_dict["has_overrun"] = "sum"
    
    if "number_of_bring_backs" in transit_df.columns:
        agg_dict["number_of_bring_backs"] = "sum"
    
    if "transit_failure_type" in transit_df.columns:
        transit_df["has_failure"] = transit_df["transit_failure_type"].fillna("") != ""
        agg_dict["has_failure"] = "sum"
    
    if "misroute" in transit_df.columns:
        transit_df["is_misroute"] = transit_df["misroute"].fillna("").str.upper() == "Y"
        agg_dict["is_misroute"] = "sum"
    
    agg = transit_df.groupby(group_col).agg(agg_dict)
    agg.columns = ["_".join(col).strip("_") for col in agg.columns]
    agg = agg.reset_index()
    
    # Rename columns
    rename_map = {
        group_col: "customer_code",
        "is_late_sum": "late_delivery_count_90d",
        "is_on_time_sum": "on_time_count_90d",
        "days_late_sum": "total_days_late_90d",
        "days_late_mean": "avg_days_late_90d",
        "is_direct_sum": "direct_shipment_count_90d",
        "has_overrun_sum": "transit_overrun_count_90d",
        "number_of_bring_backs_sum": "bring_back_count_90d",
        "has_failure_sum": "transit_failure_count_90d",
        "is_misroute_sum": "misroute_count_90d",
    }
    agg = agg.rename(columns={k: v for k, v in rename_map.items() if k in agg.columns})
    
    # Calculate rates
    if "direct_shipment_count_90d" in agg.columns:
        total = agg["direct_shipment_count_90d"].replace(0, 1)
        agg["late_delivery_rate"] = agg["late_delivery_count_90d"] / total
        agg["on_time_delivery_rate"] = agg["on_time_count_90d"] / total
    
    logger.info(f"Created transit features for {len(agg)} customers")
    return agg


def create_pickup_features(
    pickups_df: pd.DataFrame,
    customer_codes: Optional[List[str]] = None,
    reference_date: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Create pickup features from FMP030 pickup data.
    
    Cancel reason codes (PUHCANTYP):
    - M = Missed (carrier fault)
    - C = Not Ready (customer fault)
    - A = No Freight (customer fault)
    - R = Duplicate (exclude)
    - O = Other
    
    Features created:
    - missed_pickup_count_90d: Pickups missed by carrier
    - not_ready_count_90d: Customer not ready
    - no_freight_count_90d: No freight to pick up
    - total_cancel_count_90d: Total cancellations (excl duplicates)
    - completed_pickup_count_90d: Completed pickups
    - missed_pickup_rate: Missed / total requests
    - cancel_rate: Cancellations / total requests
    - rescheduled_count_90d: Rescheduled pickups
    
    Args:
        pickups_df: Pickup data from FMP030
        customer_codes: List of customer codes (shipper_code)
        reference_date: Reference date for calculations
        
    Returns:
        DataFrame with customer_code and pickup features
    """
    if reference_date is None:
        reference_date = datetime.now()
    
    pickups_df = pickups_df.copy()
    
    # Parse dates
    date_col = "req_pku_date" if "req_pku_date" in pickups_df.columns else "req_pu_date"
    if date_col in pickups_df.columns:
        pickups_df[date_col] = pd.to_datetime(pickups_df[date_col], errors="coerce")
        
        # Filter to 90-day window
        cutoff_90d = reference_date - timedelta(days=90)
        pickups_df = pickups_df[pickups_df[date_col] >= cutoff_90d]
    
    # Filter by customer (shipper_code)
    if customer_codes is not None and "shipper_code" in pickups_df.columns:
        pickups_df = pickups_df[pickups_df["shipper_code"].isin(customer_codes)]
    
    # Determine grouping column
    group_col = "shipper_code" if "shipper_code" in pickups_df.columns else "customer_code"
    
    if group_col not in pickups_df.columns:
        logger.warning("No customer grouping column found in pickup data")
        return pd.DataFrame(columns=["customer_code"])
    
    # Exclude duplicates (PUHCANTYP = 'R')
    if "puhcantyp" in pickups_df.columns:
        pickups_df = pickups_df[pickups_df["puhcantyp"] != "R"]
        
        # Create reason flags
        pickups_df["is_missed"] = pickups_df["puhcantyp"] == "M"
        pickups_df["is_not_ready"] = pickups_df["puhcantyp"] == "C"
        pickups_df["is_no_freight"] = pickups_df["puhcantyp"] == "A"
        pickups_df["is_other_cancel"] = pickups_df["puhcantyp"] == "O"
    
    # Completed vs cancelled
    if "cancel_count" in pickups_df.columns:
        pickups_df["is_cancelled"] = pickups_df["cancel_count"] == 1
        pickups_df["is_completed"] = pickups_df["cancel_count"] == 0
    elif "comp_count" in pickups_df.columns:
        pickups_df["is_completed"] = pickups_df["comp_count"] == 1
        pickups_df["is_cancelled"] = pickups_df["comp_count"] == 0
    elif "status_flag" in pickups_df.columns:
        pickups_df["is_completed"] = pickups_df["status_flag"].str.upper() == "PKU"
        pickups_df["is_cancelled"] = pickups_df["status_flag"].str.upper() == "CAN"
    
    # Rescheduled flag
    if "rescheduled" in pickups_df.columns:
        pickups_df["is_rescheduled"] = pickups_df["rescheduled"].str.upper() == "Y"
    
    # Build aggregation dict
    agg_dict = {}
    
    for col in ["is_missed", "is_not_ready", "is_no_freight", "is_other_cancel", 
                "is_completed", "is_cancelled", "is_rescheduled"]:
        if col in pickups_df.columns:
            agg_dict[col] = "sum"
    
    if not agg_dict:
        logger.warning("No pickup metrics columns available")
        return pd.DataFrame(columns=["customer_code"])
    
    # Add total count
    agg_dict[date_col] = "count"
    
    agg = pickups_df.groupby(group_col).agg(agg_dict)
    agg.columns = [col if col != date_col else "total_requests" for col in agg.columns]
    agg = agg.reset_index()
    
    # Rename columns
    rename_map = {
        group_col: "customer_code",
        "is_missed": "missed_pickup_count_90d",
        "is_not_ready": "not_ready_count_90d",
        "is_no_freight": "no_freight_count_90d",
        "is_other_cancel": "other_cancel_count_90d",
        "is_completed": "completed_pickup_count_90d",
        "is_cancelled": "cancelled_pickup_count_90d",
        "is_rescheduled": "rescheduled_count_90d",
    }
    agg = agg.rename(columns={k: v for k, v in rename_map.items() if k in agg.columns})
    
    # Calculate rates
    if "total_requests" in agg.columns:
        total = agg["total_requests"].replace(0, 1)
        if "missed_pickup_count_90d" in agg.columns:
            agg["missed_pickup_rate"] = agg["missed_pickup_count_90d"] / total
        if "cancelled_pickup_count_90d" in agg.columns:
            agg["cancel_rate"] = agg["cancelled_pickup_count_90d"] / total
    
    logger.info(f"Created pickup features for {len(agg)} customers")
    return agg


def create_claims_features(
    claims_df: pd.DataFrame,
    shipments_df: pd.DataFrame,
    customer_codes: Optional[List[str]] = None,
    reference_date: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Create claims features from Claims Data.
    
    Note: Typically 1 claim per PRO.
    
    Features created:
    - claim_count_90d: Claims in last 90 days
    - claim_count_365d: Claims in last year
    - total_claims_filed_90d: $ filed in 90 days
    - total_claims_paid_90d: $ paid in 90 days
    - claim_rate: Claims / shipments (90d)
    - avg_claim_amount: Average $ filed per claim
    - claims_by_type: Counts by claim type
    
    Args:
        claims_df: Claims data
        shipments_df: Shipment data (for calculating claim rate)
        customer_codes: List of customer codes
        reference_date: Reference date for calculations
        
    Returns:
        DataFrame with customer_code and claims features
    """
    if reference_date is None:
        reference_date = datetime.now()
    
    claims_df = claims_df.copy()
    
    # Parse dates
    date_col = "claim_acknowledged_date"
    if date_col in claims_df.columns:
        claims_df[date_col] = pd.to_datetime(claims_df[date_col], errors="coerce")
    
    # Filter by customer
    if customer_codes is not None and "customer_code" in claims_df.columns:
        claims_df = claims_df[claims_df["customer_code"].isin(customer_codes)]
    
    # Define time windows
    cutoff_90d = reference_date - timedelta(days=90)
    cutoff_365d = reference_date - timedelta(days=365)
    
    # Determine grouping column
    group_col = "customer_code"
    if group_col not in claims_df.columns:
        # Try to join via PRO to get customer
        if "pro" in claims_df.columns and "alpha_pro" in shipments_df.columns:
            pro_to_customer = shipments_df[["alpha_pro", "customer_code"]].drop_duplicates()
            pro_to_customer = pro_to_customer.rename(columns={"alpha_pro": "pro"})
            claims_df = claims_df.merge(pro_to_customer, on="pro", how="left")
    
    if group_col not in claims_df.columns:
        logger.warning("No customer grouping column found in claims data")
        return pd.DataFrame(columns=["customer_code"])
    
    # Calculate 90-day metrics
    claims_90d = claims_df[claims_df[date_col] >= cutoff_90d] if date_col in claims_df.columns else claims_df
    
    agg_90d_dict = {
        "claim_id": "count" if "claim_id" in claims_90d.columns else "size",
    }
    
    if "amount_filed" in claims_90d.columns:
        agg_90d_dict["amount_filed"] = "sum"
    if "amount_paid" in claims_90d.columns:
        agg_90d_dict["amount_paid"] = "sum"
    
    agg_90d = claims_90d.groupby(group_col).agg(agg_90d_dict).reset_index()
    
    rename_90d = {
        "claim_id": "claim_count_90d",
        "size": "claim_count_90d",
        "amount_filed": "total_claims_filed_90d",
        "amount_paid": "total_claims_paid_90d",
    }
    agg_90d = agg_90d.rename(columns={k: v for k, v in rename_90d.items() if k in agg_90d.columns})
    
    # Calculate 365-day metrics
    claims_365d = claims_df[claims_df[date_col] >= cutoff_365d] if date_col in claims_df.columns else claims_df
    
    agg_365d = claims_365d.groupby(group_col).size().reset_index(name="claim_count_365d")
    
    # Merge
    df = agg_90d.merge(agg_365d, on=group_col, how="outer").fillna(0)
    df = df.rename(columns={group_col: "customer_code"})
    
    # Average claim amount
    if "total_claims_filed_90d" in df.columns and "claim_count_90d" in df.columns:
        df["avg_claim_amount"] = df["total_claims_filed_90d"] / df["claim_count_90d"].replace(0, 1)
    
    # Claims by type (if available)
    if "claim_type" in claims_90d.columns:
        type_counts = claims_90d.groupby([group_col, "claim_type"]).size().unstack(fill_value=0)
        type_counts = type_counts.add_prefix("claims_type_")
        type_counts = type_counts.reset_index().rename(columns={group_col: "customer_code"})
        df = df.merge(type_counts, on="customer_code", how="left")
    
    # Calculate claim rate (claims / shipments)
    if len(shipments_df) > 0:
        shipments_df = shipments_df.copy()
        shipments_df["pickup_date"] = pd.to_datetime(shipments_df["pickup_date"], errors="coerce")
        shipments_90d = shipments_df[shipments_df["pickup_date"] >= cutoff_90d]
        
        shipment_counts = shipments_90d.groupby("customer_code").size().reset_index(name="shipment_count_90d")
        df = df.merge(shipment_counts, on="customer_code", how="left")
        df["shipment_count_90d"] = df["shipment_count_90d"].fillna(0)
        
        df["claim_rate"] = df["claim_count_90d"] / df["shipment_count_90d"].replace(0, 1)
    
    logger.info(f"Created claims features for {len(df)} customers")
    return df


def create_service_center_features(
    shipments_df: pd.DataFrame,
    transit_df: pd.DataFrame,
    customer_codes: Optional[List[str]] = None,
    reference_date: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Create service center related features.
    
    Features created:
    - distinct_service_centers: Number of unique service centers used
    - primary_service_center: Most frequent service center
    - primary_sc_volume_pct: % of volume at primary service center
    - service_center_issue_rate: % of issues at primary center
    
    Args:
        shipments_df: Shipment data with service center info
        transit_df: Transit data with late/failure flags
        customer_codes: List of customer codes
        reference_date: Reference date for calculations
        
    Returns:
        DataFrame with customer_code and service center features
    """
    if reference_date is None:
        reference_date = datetime.now()
    
    cutoff_90d = reference_date - timedelta(days=90)
    
    shipments_df = shipments_df.copy()
    if "pickup_date" in shipments_df.columns:
        shipments_df["pickup_date"] = pd.to_datetime(shipments_df["pickup_date"], errors="coerce")
        shipments_df = shipments_df[shipments_df["pickup_date"] >= cutoff_90d]
    
    if customer_codes is not None and "customer_code" in shipments_df.columns:
        shipments_df = shipments_df[shipments_df["customer_code"].isin(customer_codes)]
    
    if "customer_code" not in shipments_df.columns or len(shipments_df) == 0:
        logger.warning("No customer_code or shipment data for service center features")
        return pd.DataFrame(columns=["customer_code"])
    
    # Determine service center column
    sc_col = "origin_service_center" if "origin_service_center" in shipments_df.columns else "ori_id"
    if sc_col not in shipments_df.columns:
        logger.warning("No service center column found")
        return pd.DataFrame(columns=["customer_code"])
    
    # Distinct service centers
    distinct_sc = shipments_df.groupby("customer_code")[sc_col].nunique().reset_index()
    distinct_sc.columns = ["customer_code", "distinct_service_centers"]
    
    # Primary service center (mode)
    primary_sc = shipments_df.groupby("customer_code")[sc_col].agg(
        lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else None
    ).reset_index()
    primary_sc.columns = ["customer_code", "primary_service_center"]
    
    # Primary SC volume percentage
    sc_counts = shipments_df.groupby(["customer_code", sc_col]).size().reset_index(name="count")
    total_counts = sc_counts.groupby("customer_code")["count"].sum().reset_index(name="total")
    sc_counts = sc_counts.merge(total_counts, on="customer_code")
    sc_counts["pct"] = sc_counts["count"] / sc_counts["total"]
    
    primary_pct = sc_counts.loc[sc_counts.groupby("customer_code")["count"].idxmax()][
        ["customer_code", "pct"]
    ].rename(columns={"pct": "primary_sc_volume_pct"})
    
    # Merge
    df = distinct_sc.merge(primary_sc, on="customer_code", how="left")
    df = df.merge(primary_pct, on="customer_code", how="left")
    
    logger.info(f"Created service center features for {len(df)} customers")
    return df


def create_shipper_consignee_features(
    shipments_df: pd.DataFrame,
    customer_codes: Optional[List[str]] = None,
    reference_date: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Create shipper/consignee lane features.
    
    Features created:
    - distinct_shippers: Number of unique shippers
    - distinct_consignees: Number of unique consignees
    - distinct_lanes: Number of unique shipper-consignee pairs
    - top_lane_concentration: % volume in top lane
    
    Args:
        shipments_df: Shipment data
        customer_codes: List of customer codes
        reference_date: Reference date for calculations
        
    Returns:
        DataFrame with customer_code and lane features
    """
    if reference_date is None:
        reference_date = datetime.now()
    
    cutoff_90d = reference_date - timedelta(days=90)
    
    shipments_df = shipments_df.copy()
    if "pickup_date" in shipments_df.columns:
        shipments_df["pickup_date"] = pd.to_datetime(shipments_df["pickup_date"], errors="coerce")
        shipments_df = shipments_df[shipments_df["pickup_date"] >= cutoff_90d]
    
    if customer_codes is not None and "customer_code" in shipments_df.columns:
        shipments_df = shipments_df[shipments_df["customer_code"].isin(customer_codes)]
    
    if "customer_code" not in shipments_df.columns or len(shipments_df) == 0:
        return pd.DataFrame(columns=["customer_code"])
    
    results = []
    
    # Distinct shippers
    if "shipper_code" in shipments_df.columns:
        shippers = shipments_df.groupby("customer_code")["shipper_code"].nunique().reset_index()
        shippers.columns = ["customer_code", "distinct_shippers"]
        results.append(shippers)
    
    # Distinct consignees
    if "consignee_code" in shipments_df.columns:
        consignees = shipments_df.groupby("customer_code")["consignee_code"].nunique().reset_index()
        consignees.columns = ["customer_code", "distinct_consignees"]
        results.append(consignees)
    
    # Distinct lanes and top lane concentration
    if "shipper_code" in shipments_df.columns and "consignee_code" in shipments_df.columns:
        shipments_df["lane"] = shipments_df["shipper_code"].astype(str) + "_" + shipments_df["consignee_code"].astype(str)
        
        lanes = shipments_df.groupby("customer_code")["lane"].nunique().reset_index()
        lanes.columns = ["customer_code", "distinct_lanes"]
        results.append(lanes)
        
        # Top lane concentration
        lane_counts = shipments_df.groupby(["customer_code", "lane"]).size().reset_index(name="count")
        total_counts = lane_counts.groupby("customer_code")["count"].sum().reset_index(name="total")
        lane_counts = lane_counts.merge(total_counts, on="customer_code")
        lane_counts["pct"] = lane_counts["count"] / lane_counts["total"]
        
        top_lane = lane_counts.loc[lane_counts.groupby("customer_code")["count"].idxmax()][
            ["customer_code", "pct"]
        ].rename(columns={"pct": "top_lane_concentration"})
        results.append(top_lane)
    
    if not results:
        return pd.DataFrame(columns=["customer_code"])
    
    # Merge all results
    df = results[0]
    for r in results[1:]:
        df = df.merge(r, on="customer_code", how="outer")
    
    logger.info(f"Created shipper/consignee features for {len(df)} customers")
    return df


def create_all_features(
    customers_df: pd.DataFrame,
    shipments_df: pd.DataFrame,
    transit_df: pd.DataFrame,
    pickups_df: pd.DataFrame,
    claims_df: pd.DataFrame,
    reference_date: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Create all LTL freight churn prediction features.
    
    Combines features from:
    - Tenure (from shipment history)
    - Shipment activity and revenue
    - Transit/delivery performance (on-time, late, days late)
    - Pickup performance (missed, cancelled, not ready)
    - Claims (count, rate, amounts)
    - Service center usage
    - Shipper/consignee lane concentration
    
    Args:
        customers_df: Customer master data with customer_code
        shipments_df: Shipment data from FRP001
        transit_df: Transit performance from TransitReview_V03
        pickups_df: Pickup data from FMP030
        claims_df: Claims data
        reference_date: Reference date for calculations
        
    Returns:
        Complete feature matrix with customer_code
    """
    if reference_date is None:
        reference_date = datetime.now()
    
    logger.info(f"Creating all LTL freight features as of {reference_date.date()}")
    
    # Start with all customers
    customer_codes = customers_df["customer_code"].tolist()
    features = customers_df[["customer_code"]].copy()
    
    # 1. Tenure features
    logger.info("Creating tenure features...")
    tenure_features = create_tenure_features(customers_df, shipments_df, reference_date)
    features = features.merge(tenure_features, on="customer_code", how="left")
    
    # 2. Shipment and revenue features
    logger.info("Creating shipment features...")
    shipment_features = create_shipment_features(shipments_df, customer_codes, reference_date)
    features = features.merge(shipment_features, on="customer_code", how="left")
    
    # 3. Transit/delivery features
    logger.info("Creating transit features...")
    transit_features = create_transit_features(transit_df, customer_codes, reference_date)
    features = features.merge(transit_features, on="customer_code", how="left")
    
    # 4. Pickup features
    logger.info("Creating pickup features...")
    pickup_features = create_pickup_features(pickups_df, customer_codes, reference_date)
    features = features.merge(pickup_features, on="customer_code", how="left")
    
    # 5. Claims features
    logger.info("Creating claims features...")
    claims_features = create_claims_features(claims_df, shipments_df, customer_codes, reference_date)
    features = features.merge(claims_features, on="customer_code", how="left")
    
    # 6. Service center features
    logger.info("Creating service center features...")
    sc_features = create_service_center_features(shipments_df, transit_df, customer_codes, reference_date)
    features = features.merge(sc_features, on="customer_code", how="left")
    
    # 7. Shipper/consignee features
    logger.info("Creating shipper/consignee features...")
    lane_features = create_shipper_consignee_features(shipments_df, customer_codes, reference_date)
    features = features.merge(lane_features, on="customer_code", how="left")
    
    # Fill missing numeric values with 0
    numeric_cols = features.select_dtypes(include=[np.number]).columns
    features[numeric_cols] = features[numeric_cols].fillna(0)
    
    # Special handling for days_since columns (no shipments = very long time)
    for col in features.columns:
        if col.startswith("days_since"):
            features[col] = features[col].replace(0, 9999)
    
    # Fill missing rates with 0
    rate_cols = [c for c in features.columns if c.endswith("_rate")]
    for col in rate_cols:
        features[col] = features[col].fillna(0)
    
    feature_count = len(features.columns) - 1  # Exclude customer_code
    logger.info(f"Created {feature_count} features for {len(features)} customers")
    
    return features

"""
Delta Table Schema Definitions for LTL Freight Churn Prediction.

This module defines the schemas for all Delta tables used in the
churn prediction project. Designed for Microsoft Fabric Lakehouse
with LTL freight operational data.

Source Systems:
- FRP001: Shipment data (PRO, pickup/delivery dates, revenue)
- TOP006: Customer master and revenue data
- Claims Data: Claims against shipments
- Operational Tables: Transformed into operations_events

Use create_all_tables_sql() to generate CREATE TABLE statements for Fabric.
"""

from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class ColumnDef:
    """Column definition for Delta table."""
    name: str
    data_type: str
    nullable: bool = True
    description: str = ""


@dataclass
class TableSchema:
    """Schema definition for a Delta table."""
    name: str
    columns: List[ColumnDef]
    primary_key: List[str]
    business_key: List[str] = None
    description: str = ""
    source_system: str = ""


# =============================================================================
# Table Schemas - LTL Freight Data Model
# =============================================================================

CUSTOMERS_SCHEMA = TableSchema(
    name="customers",
    description="Customer master data from TOP006",
    source_system="TOP006",
    primary_key=["customer_code"],
    columns=[
        ColumnDef("customer_code", "STRING", False, "Primary key - customer identifier from TOP006"),
        ColumnDef("customer_name", "STRING", True, "Customer business name"),
        ColumnDef("segment", "STRING", True, "Customer segment (National, Regional, SMB)"),
        ColumnDef("industry", "STRING", True, "Industry classification"),
        ColumnDef("start_date", "DATE", True, "Customer relationship start date"),
        ColumnDef("sales_rep", "STRING", True, "Assigned sales representative"),
        ColumnDef("region", "STRING", True, "Geographic region"),
        ColumnDef("is_active", "BOOLEAN", True, "Current active status"),
        ColumnDef("created_at", "TIMESTAMP", False, "Record creation timestamp"),
        ColumnDef("updated_at", "TIMESTAMP", True, "Last update timestamp"),
    ]
)

AGREEMENTS_SCHEMA = TableSchema(
    name="agreements",
    description="Pricing agreements linking customers to shipments",
    source_system="FRP001/Contract System",
    primary_key=["agreement_id"],
    business_key=["agreement_number"],
    columns=[
        ColumnDef("agreement_id", "STRING", False, "Unique agreement identifier (UUID)"),
        ColumnDef("agreement_number", "STRING", False, "Business agreement number"),
        ColumnDef("customer_code", "STRING", False, "FK to customers.customer_code"),
        ColumnDef("agreement_type", "STRING", True, "Type (Spot, Contract, Volume)"),
        ColumnDef("effective_date", "DATE", True, "Agreement start date"),
        ColumnDef("expiration_date", "DATE", True, "Agreement end date"),
        ColumnDef("status", "STRING", True, "Active, Expired, Cancelled"),
        ColumnDef("created_at", "TIMESTAMP", False, "Record creation timestamp"),
    ]
)

SHIPPERS_SCHEMA = TableSchema(
    name="shippers",
    description="Shipper (origin) reference dimension",
    source_system="Master Data",
    primary_key=["shipper_code"],
    columns=[
        ColumnDef("shipper_code", "STRING", False, "Primary key - shipper identifier"),
        ColumnDef("shipper_name", "STRING", True, "Shipper business name"),
        ColumnDef("shipper_city", "STRING", True, "City"),
        ColumnDef("shipper_state", "STRING", True, "State code"),
        ColumnDef("shipper_zip", "STRING", True, "ZIP code"),
        ColumnDef("customer_code", "STRING", True, "FK to customers if shipper is the customer"),
        ColumnDef("created_at", "TIMESTAMP", False, "Record creation timestamp"),
    ]
)

CONSIGNEES_SCHEMA = TableSchema(
    name="consignees",
    description="Consignee (destination) reference dimension",
    source_system="Master Data",
    primary_key=["consignee_code"],
    columns=[
        ColumnDef("consignee_code", "STRING", False, "Primary key - consignee identifier"),
        ColumnDef("consignee_name", "STRING", True, "Consignee business name"),
        ColumnDef("consignee_city", "STRING", True, "City"),
        ColumnDef("consignee_state", "STRING", True, "State code"),
        ColumnDef("consignee_zip", "STRING", True, "ZIP code"),
        ColumnDef("customer_code", "STRING", True, "FK to customers if consignee is the customer"),
        ColumnDef("created_at", "TIMESTAMP", False, "Record creation timestamp"),
    ]
)

SHIPMENTS_SCHEMA = TableSchema(
    name="shipments",
    description="Shipment facts from FRP001 - one row per PRO",
    source_system="FRP001",
    primary_key=["shipment_id"],
    business_key=["alpha_pro"],
    columns=[
        ColumnDef("shipment_id", "STRING", False, "Unique ID (UUID)"),
        ColumnDef("alpha_pro", "STRING", False, "Alpha PRO number (primary business key)"),
        ColumnDef("agreement_number", "STRING", True, "FK to agreements.agreement_number"),
        ColumnDef("customer_code", "STRING", True, "FK to customers (denormalized)"),
        ColumnDef("shipper_code", "STRING", True, "FK to shippers.shipper_code"),
        ColumnDef("consignee_code", "STRING", True, "FK to consignees.consignee_code"),
        ColumnDef("pickup_date", "DATE", True, "Actual pickup date"),
        ColumnDef("delivery_date", "DATE", True, "Actual delivery date"),
        ColumnDef("scheduled_delivery_date", "DATE", True, "Originally scheduled delivery date"),
        ColumnDef("origin_service_center", "STRING", True, "Pickup service center code"),
        ColumnDef("dest_service_center", "STRING", True, "Delivery service center code"),
        ColumnDef("weight", "DECIMAL(10,2)", True, "Shipment weight in lbs"),
        ColumnDef("pieces", "INT", True, "Number of pieces"),
        ColumnDef("revenue", "DECIMAL(12,2)", True, "Shipment revenue"),
        ColumnDef("created_at", "TIMESTAMP", False, "Record creation timestamp"),
    ]
)

OPERATIONS_EVENTS_SCHEMA = TableSchema(
    name="operations_events",
    description="Service failures - boolean flags + days late per PRO",
    source_system="Transformed from operational tables",
    primary_key=["event_id"],
    business_key=["alpha_pro"],
    columns=[
        ColumnDef("event_id", "STRING", False, "Unique ID (UUID)"),
        ColumnDef("alpha_pro", "STRING", False, "FK to shipments.alpha_pro"),
        ColumnDef("is_missed_pickup", "BOOLEAN", True, "Pickup was missed (True/False)"),
        ColumnDef("is_late_delivery", "BOOLEAN", True, "Delivery was late (True/False)"),
        ColumnDef("days_late", "INT", True, "Number of days late (0 if on-time)"),
        ColumnDef("is_cancelled_pickup", "BOOLEAN", True, "Pickup was cancelled (True/False)"),
        ColumnDef("responsible_service_center", "STRING", True, "Service center responsible for issue"),
        ColumnDef("event_date", "DATE", True, "Date of the primary event"),
        ColumnDef("created_at", "TIMESTAMP", False, "Record creation timestamp"),
    ]
)

CLAIMS_SCHEMA = TableSchema(
    name="claims",
    description="Claims filed against shipments",
    source_system="Claims Data",
    primary_key=["claim_id"],
    columns=[
        ColumnDef("claim_id", "STRING", False, "Primary key - claim identifier"),
        ColumnDef("pro", "STRING", False, "PRO number (FK to shipments.alpha_pro)"),
        ColumnDef("customer_code", "STRING", True, "FK to customers (denormalized)"),
        ColumnDef("claim_acknowledged_date", "DATE", True, "Date claim was acknowledged"),
        ColumnDef("amount_filed", "DECIMAL(12,2)", True, "Dollar amount filed"),
        ColumnDef("amount_approved", "DECIMAL(12,2)", True, "Dollar amount approved"),
        ColumnDef("amount_paid", "DECIMAL(12,2)", True, "Dollar amount paid"),
        ColumnDef("claim_type", "STRING", True, "Type of claim (Damage, Loss, Shortage, etc.)"),
        ColumnDef("claim_status", "STRING", True, "Current status (Open, Paid, Denied)"),
        ColumnDef("created_at", "TIMESTAMP", False, "Record creation timestamp"),
    ]
)

CUSTOMER_REVENUE_SCHEMA = TableSchema(
    name="customer_revenue",
    description="Revenue aggregation per customer per period",
    source_system="TOP006",
    primary_key=["revenue_id"],
    columns=[
        ColumnDef("revenue_id", "STRING", False, "Unique ID (UUID)"),
        ColumnDef("customer_code", "STRING", False, "FK to customers.customer_code"),
        ColumnDef("period_date", "DATE", False, "First day of period"),
        ColumnDef("period_type", "STRING", True, "MONTHLY or WEEKLY"),
        ColumnDef("shipment_count", "INT", True, "Number of shipments in period"),
        ColumnDef("total_revenue", "DECIMAL(14,2)", True, "Total revenue in period"),
        ColumnDef("total_weight", "DECIMAL(14,2)", True, "Total weight shipped"),
        ColumnDef("avg_revenue_per_shipment", "DECIMAL(10,2)", True, "Average revenue per shipment"),
        ColumnDef("created_at", "TIMESTAMP", False, "Record creation timestamp"),
    ]
)

FEATURES_SCHEMA = TableSchema(
    name="features",
    description="Computed features for ML model input - one row per customer per scoring date",
    source_system="Computed",
    primary_key=["feature_id"],
    columns=[
        ColumnDef("feature_id", "STRING", False, "Unique feature record identifier"),
        ColumnDef("customer_code", "STRING", False, "FK to customers.customer_code"),
        ColumnDef("feature_set_id", "STRING", False, "Version identifier for feature set"),
        ColumnDef("computed_date", "DATE", False, "Date features were computed"),
        # Tenure Features
        ColumnDef("tenure_days", "INT", True, "Days since first shipment"),
        ColumnDef("tenure_months", "INT", True, "Months since first shipment"),
        # Activity Features
        ColumnDef("shipment_count_30d", "INT", True, "Shipments in last 30 days"),
        ColumnDef("shipment_count_60d", "INT", True, "Shipments in last 60 days"),
        ColumnDef("shipment_count_90d", "INT", True, "Shipments in last 90 days"),
        ColumnDef("days_since_last_shipment", "INT", True, "Days since most recent shipment"),
        # Revenue Features
        ColumnDef("revenue_30d", "DECIMAL(12,2)", True, "Revenue last 30 days"),
        ColumnDef("revenue_60d", "DECIMAL(12,2)", True, "Revenue last 60 days"),
        ColumnDef("revenue_90d", "DECIMAL(12,2)", True, "Revenue last 90 days"),
        ColumnDef("revenue_trend", "DECIMAL(8,4)", True, "Revenue change (recent vs prior period)"),
        ColumnDef("avg_revenue_per_shipment", "DECIMAL(10,2)", True, "Average revenue per shipment"),
        # Operations Features
        ColumnDef("missed_pickup_count_90d", "INT", True, "Missed pickups in 90 days"),
        ColumnDef("late_delivery_count_90d", "INT", True, "Late deliveries in 90 days"),
        ColumnDef("cancelled_pickup_count_90d", "INT", True, "Cancelled pickups in 90 days"),
        ColumnDef("avg_days_late_90d", "DECIMAL(6,2)", True, "Average days late in 90 days"),
        ColumnDef("missed_pickup_rate", "DECIMAL(6,4)", True, "% of shipments with missed pickup"),
        ColumnDef("late_delivery_rate", "DECIMAL(6,4)", True, "% of shipments delivered late"),
        ColumnDef("on_time_delivery_rate", "DECIMAL(6,4)", True, "% of shipments on-time"),
        # Interline Features
        ColumnDef("interline_count_90d", "INT", True, "Interline shipments in 90 days"),
        ColumnDef("interline_pct", "DECIMAL(6,4)", True, "% of shipments that are interline"),
        # Claims Features
        ColumnDef("claim_count_90d", "INT", True, "Claims in last 90 days"),
        ColumnDef("claim_count_365d", "INT", True, "Claims in last year"),
        ColumnDef("total_claims_filed_90d", "DECIMAL(12,2)", True, "$ claims filed in 90 days"),
        ColumnDef("total_claims_paid_90d", "DECIMAL(12,2)", True, "$ claims paid in 90 days"),
        ColumnDef("claim_rate", "DECIMAL(6,4)", True, "Claims per shipment"),
        ColumnDef("avg_claim_amount", "DECIMAL(10,2)", True, "Average claim amount"),
        # Service Center Features
        ColumnDef("distinct_service_centers", "INT", True, "Number of service centers used"),
        ColumnDef("primary_service_center", "STRING", True, "Most frequent service center"),
        ColumnDef("service_center_issue_rate", "DECIMAL(6,4)", True, "% issues at primary center"),
        # Door Pressure Features
        ColumnDef("primary_sc_avg_pressure", "DECIMAL(6,4)", True, "Average door pressure at primary SC (90d)"),
        ColumnDef("primary_sc_max_pressure", "DECIMAL(6,4)", True, "Peak door pressure at primary SC (90d)"),
        ColumnDef("high_pressure_shipment_pct", "DECIMAL(6,4)", True, "% of shipments during high-pressure days"),
        ColumnDef("weighted_pressure_exposure", "DECIMAL(6,4)", True, "Ship-weighted average pressure exposure"),
        # Shipper/Consignee Features
        ColumnDef("distinct_shippers", "INT", True, "Number of unique shippers"),
        ColumnDef("distinct_consignees", "INT", True, "Number of unique consignees"),
        ColumnDef("top_lane_concentration", "DECIMAL(6,4)", True, "% volume in top shipper-consignee lane"),
        # Lane Abandonment Features
        ColumnDef("lanes_abandoned_90d", "INT", True, "Lanes active 90-180d ago with 0 recent shipments"),
        ColumnDef("lanes_abandoned_pct", "DECIMAL(6,4)", True, "% of historical lanes abandoned"),
        ColumnDef("new_lanes_90d", "INT", True, "New lanes started in last 90 days"),
        ColumnDef("lane_churn_rate", "DECIMAL(6,4)", True, "Net lane change rate (new - abandoned) / total"),
        ColumnDef("created_at", "TIMESTAMP", False, "Record creation timestamp"),
    ]
)

PREDICTIONS_SCHEMA = TableSchema(
    name="predictions",
    description="Model prediction outputs - one row per customer per bucket per date",
    source_system="ML Model",
    primary_key=["prediction_id"],
    columns=[
        ColumnDef("prediction_id", "STRING", False, "Unique prediction identifier"),
        ColumnDef("customer_code", "STRING", False, "FK to customers.customer_code"),
        ColumnDef("prediction_date", "DATE", False, "Date prediction was generated"),
        ColumnDef("model_version", "STRING", False, "Model version used for prediction"),
        ColumnDef("churn_bucket", "STRING", False, "churn_30d, churn_60d, churn_90d, revenue_decline"),
        ColumnDef("churn_probability", "DECIMAL(6,4)", False, "Predicted probability (0.0-1.0)"),
        ColumnDef("risk_tier", "STRING", False, "Low, Medium, High, Critical"),
        ColumnDef("previous_probability", "DECIMAL(6,4)", True, "Previous week probability"),
        ColumnDef("probability_change", "DECIMAL(6,4)", True, "Week-over-week change"),
        ColumnDef("alert_triggered", "BOOLEAN", True, "True if crossed risk threshold"),
        ColumnDef("created_at", "TIMESTAMP", False, "Record creation timestamp"),
    ]
)

CHURN_EVENTS_SCHEMA = TableSchema(
    name="churn_events",
    description="Actual churn outcomes for model training/validation",
    source_system="Derived",
    primary_key=["churn_event_id"],
    columns=[
        ColumnDef("churn_event_id", "STRING", False, "Unique churn event identifier"),
        ColumnDef("customer_code", "STRING", False, "FK to customers.customer_code"),
        ColumnDef("event_date", "DATE", False, "Date churn was identified"),
        ColumnDef("churn_type", "STRING", False, "inactivity_30d, inactivity_60d, inactivity_90d, revenue_decline, contract_cancellation"),
        ColumnDef("revenue_at_churn", "DECIMAL(12,2)", True, "Last period revenue before churn"),
        ColumnDef("shipments_at_churn", "INT", True, "Last period shipment count"),
        ColumnDef("created_at", "TIMESTAMP", False, "Record creation timestamp"),
    ]
)

MODEL_METRICS_SCHEMA = TableSchema(
    name="model_metrics",
    description="Model performance metrics for tracking and comparison",
    source_system="MLflow",
    primary_key=["metrics_id"],
    columns=[
        ColumnDef("metrics_id", "STRING", False, "Unique metrics record identifier"),
        ColumnDef("model_version", "STRING", False, "Model version identifier"),
        ColumnDef("churn_bucket", "STRING", False, "Churn bucket this model predicts"),
        ColumnDef("training_date", "DATE", False, "Date model was trained"),
        ColumnDef("auc_roc", "DECIMAL(5,4)", False, "Area under ROC curve"),
        ColumnDef("auc_pr", "DECIMAL(5,4)", True, "Area under Precision-Recall curve"),
        ColumnDef("accuracy", "DECIMAL(5,4)", True, "Overall accuracy"),
        ColumnDef("precision_score", "DECIMAL(5,4)", True, "Precision for positive class"),
        ColumnDef("recall_score", "DECIMAL(5,4)", True, "Recall for positive class"),
        ColumnDef("f1_score", "DECIMAL(5,4)", True, "F1 score"),
        ColumnDef("train_samples", "INT", True, "Number of training samples"),
        ColumnDef("test_samples", "INT", True, "Number of test samples"),
        ColumnDef("cv_mean_auc", "DECIMAL(5,4)", True, "Mean CV AUC-ROC"),
        ColumnDef("cv_std_auc", "DECIMAL(5,4)", True, "Std dev of CV AUC-ROC"),
        ColumnDef("hyperparameters_json", "STRING", True, "Model hyperparameters as JSON"),
        ColumnDef("mlflow_run_id", "STRING", True, "MLflow run identifier"),
        ColumnDef("created_at", "TIMESTAMP", False, "Record creation timestamp"),
    ]
)

FEATURE_IMPORTANCE_SCHEMA = TableSchema(
    name="feature_importance",
    description="Feature importance scores with statistical significance",
    source_system="ML Model",
    primary_key=["importance_id"],
    columns=[
        ColumnDef("importance_id", "STRING", False, "Unique importance record identifier"),
        ColumnDef("model_version", "STRING", False, "Model version identifier"),
        ColumnDef("churn_bucket", "STRING", False, "Churn bucket this importance relates to"),
        ColumnDef("feature_name", "STRING", False, "Name of the feature"),
        ColumnDef("coefficient", "DECIMAL(10,6)", False, "Logistic regression coefficient"),
        ColumnDef("odds_ratio", "DECIMAL(10,4)", False, "Odds ratio (exp of coefficient)"),
        ColumnDef("std_error", "DECIMAL(10,6)", True, "Standard error of coefficient"),
        ColumnDef("z_score", "DECIMAL(10,4)", True, "Z-score for significance test"),
        ColumnDef("p_value", "DECIMAL(10,6)", True, "P-value for coefficient"),
        ColumnDef("ci_lower", "DECIMAL(10,6)", True, "95% CI lower bound"),
        ColumnDef("ci_upper", "DECIMAL(10,6)", True, "95% CI upper bound"),
        ColumnDef("importance_rank", "INT", False, "Rank by absolute coefficient"),
        ColumnDef("is_significant", "BOOLEAN", True, "Whether p_value < 0.05"),
        ColumnDef("created_at", "TIMESTAMP", False, "Record creation timestamp"),
    ]
)

POLICIES_SCHEMA = TableSchema(
    name="policies",
    description="Retention policies and interventions",
    source_system="Business",
    primary_key=["policy_id"],
    columns=[
        ColumnDef("policy_id", "STRING", False, "Unique policy identifier"),
        ColumnDef("policy_name", "STRING", False, "Display name for policy"),
        ColumnDef("policy_type", "STRING", False, "Type (discount, outreach, service_recovery)"),
        ColumnDef("description", "STRING", True, "Detailed policy description"),
        ColumnDef("start_date", "DATE", False, "Policy effective start date"),
        ColumnDef("end_date", "DATE", True, "Policy end date (null if ongoing)"),
        ColumnDef("target_segment", "STRING", True, "Target customer segment"),
        ColumnDef("target_risk_tier", "STRING", True, "Target risk tier (High, Critical)"),
        ColumnDef("is_active", "BOOLEAN", True, "Whether policy is currently active"),
        ColumnDef("created_at", "TIMESTAMP", False, "Record creation timestamp"),
        ColumnDef("updated_at", "TIMESTAMP", True, "Record last update timestamp"),
    ]
)

POLICY_COHORTS_SCHEMA = TableSchema(
    name="policy_cohorts",
    description="Customer assignments to policy treatment and control groups",
    source_system="Business",
    primary_key=["cohort_id"],
    columns=[
        ColumnDef("cohort_id", "STRING", False, "Unique cohort assignment identifier"),
        ColumnDef("policy_id", "STRING", False, "FK to policies.policy_id"),
        ColumnDef("customer_code", "STRING", False, "FK to customers.customer_code"),
        ColumnDef("cohort_type", "STRING", False, "treatment or control"),
        ColumnDef("assignment_date", "DATE", False, "Date customer was assigned"),
        ColumnDef("risk_score_at_assignment", "DECIMAL(5,4)", True, "Churn probability when assigned"),
        ColumnDef("outcome_measured", "BOOLEAN", True, "Whether outcome has been measured"),
        ColumnDef("outcome_date", "DATE", True, "Date outcome was measured"),
        ColumnDef("did_churn", "BOOLEAN", True, "Whether customer churned (outcome)"),
        ColumnDef("created_at", "TIMESTAMP", False, "Record creation timestamp"),
    ]
)


# =============================================================================
# Source Tables - TransitReview and Pickups
# =============================================================================

TRANSIT_REVIEW_SCHEMA = TableSchema(
    name="transit_review",
    description="Transit performance data from TransitReview_V03 - on-time/late deliveries",
    source_system="TransitReview_V03",
    primary_key=["transit_id"],
    business_key=["pro"],
    columns=[
        ColumnDef("transit_id", "STRING", False, "Unique record identifier (UUID)"),
        ColumnDef("pro", "STRING", False, "PRO number"),
        ColumnDef("pro_sfx", "STRING", True, "PRO suffix"),
        ColumnDef("ori_id", "STRING", True, "Origin service center ID"),
        ColumnDef("dst_id", "STRING", True, "Destination service center ID"),
        ColumnDef("ori_zip", "STRING", True, "Origin ZIP code"),
        ColumnDef("dst_zip", "STRING", True, "Destination ZIP code"),
        ColumnDef("pu_date", "DATE", True, "Pickup date"),
        ColumnDef("dlv_date", "DATE", True, "Actual delivery date"),
        ColumnDef("dlv_date_adj", "DATE", True, "Delivery date adjusted for weekends"),
        ColumnDef("original_edd", "DATE", True, "Original estimated delivery date"),
        ColumnDef("est_delivery_date", "DATE", True, "Estimated delivery date"),
        ColumnDef("anticipated_delvy_date", "DATE", True, "Anticipated delivery date"),
        ColumnDef("apt_date", "DATE", True, "Appointment date if set"),
        ColumnDef("agreement_number", "STRING", True, "Agreement number"),
        ColumnDef("shipper_code", "STRING", True, "Shipper code"),
        ColumnDef("consignee_code", "STRING", True, "Consignee code"),
        ColumnDef("from_carrier", "STRING", True, "Interline from carrier (empty if direct)"),
        ColumnDef("to_carrier", "STRING", True, "Interline to carrier (empty if direct)"),
        ColumnDef("std_trans_days", "INT", True, "Standard transit days"),
        ColumnDef("added_days", "INT", True, "Added days"),
        ColumnDef("carrier_added_days", "INT", True, "Carrier added days"),
        ColumnDef("service_days", "INT", True, "Service days"),
        ColumnDef("transit_days_overrun", "INT", True, "Days over standard transit"),
        ColumnDef("sign_for_overunder", "INT", True, "Sign for over/under"),
        ColumnDef("number_of_bring_backs", "INT", True, "Number of bring-back attempts"),
        ColumnDef("hazardous_material_flag", "STRING", True, "Hazmat flag"),
        ColumnDef("returned_flag", "STRING", True, "Returned shipment flag"),
        ColumnDef("transit_time_code", "STRING", True, "Service codes"),
        ColumnDef("all_short", "STRING", True, "All short flag"),
        ColumnDef("misroute", "STRING", True, "Misroute flag"),
        ColumnDef("late_departure_lh", "STRING", True, "Late departure linehaul"),
        ColumnDef("late_arrival_lh", "STRING", True, "Late arrival linehaul"),
        ColumnDef("transit_failure_type", "STRING", True, "Dispatch transit failure codes"),
        ColumnDef("customerid", "STRING", True, "Customer ID"),
        # Calculated fields
        ColumnDef("is_intra", "BOOLEAN", True, "Intra-terminal (ORI=DST)"),
        ColumnDef("is_intl", "BOOLEAN", True, "International (has carrier)"),
        ColumnDef("on_time_direct", "BOOLEAN", True, "On-time direct shipment"),
        ColumnDef("late_sql_direct", "BOOLEAN", True, "Late direct shipment"),
        ColumnDef("days_late", "INT", True, "Days late (0 if on-time)"),
        ColumnDef("created_at", "TIMESTAMP", False, "Record creation timestamp"),
    ]
)

PICKUPS_SCHEMA = TableSchema(
    name="pickups",
    description="Pickup requests from FMP030 - completed, missed, cancelled, not ready",
    source_system="FMP030",
    primary_key=["pickup_id"],
    business_key=["pu_request_number"],
    columns=[
        ColumnDef("pickup_id", "STRING", False, "Unique record identifier (UUID)"),
        ColumnDef("pu_request_number", "STRING", False, "Pickup request number"),
        ColumnDef("service_center", "STRING", True, "Pickup terminal (PKU_TERMINAL)"),
        ColumnDef("pku_region", "STRING", True, "Pickup region"),
        ColumnDef("pku_route", "STRING", True, "Pickup route name"),
        ColumnDef("status_flag", "STRING", True, "PKU (completed) or CAN (cancelled)"),
        ColumnDef("attempted", "STRING", True, "Y if attempted pickup"),
        ColumnDef("rescheduled", "STRING", True, "Rescheduled flag"),
        ColumnDef("shipper_code", "STRING", True, "Shipper number"),
        ColumnDef("shipper_name", "STRING", True, "Shipper name"),
        ColumnDef("shipper_city", "STRING", True, "Shipper city"),
        ColumnDef("shipper_state", "STRING", True, "Shipper state"),
        ColumnDef("shipper_zip", "STRING", True, "Shipper ZIP code"),
        ColumnDef("country", "STRING", True, "Country (US or Canada based on ZIP)"),
        ColumnDef("req_pku_date", "DATE", True, "Requested pickup date"),
        ColumnDef("driver_eid", "STRING", True, "Driver EID"),
        ColumnDef("cancel_reason", "STRING", True, "Cancel reason (Missed/Not Ready/No Freight/etc)"),
        ColumnDef("puhcantyp", "STRING", True, "Cancel type code (M/C/A/R/O)"),
        ColumnDef("cancel_count", "INT", True, "1 if cancelled, 0 if completed"),
        ColumnDef("comp_count", "INT", True, "1 if completed, 0 if cancelled"),
        ColumnDef("stops", "INT", True, "Number of stops"),
        ColumnDef("puh_create_type", "STRING", True, "Create type"),
        ColumnDef("entered_date", "DATE", True, "Entered date"),
        ColumnDef("entered_time", "TIME", True, "Entered time"),
        ColumnDef("sent_date", "DATE", True, "Sent to driver date"),
        ColumnDef("sent_time", "TIME", True, "Sent to driver time"),
        ColumnDef("cancel_date", "DATE", True, "Cancellation date"),
        ColumnDef("cancel_time", "TIME", True, "Cancellation time"),
        ColumnDef("pu_date", "DATE", True, "Actual pickup date"),
        ColumnDef("pu_time", "TIME", True, "Actual pickup time"),
        ColumnDef("close_date", "DATE", True, "Close date"),
        ColumnDef("close_time", "TIME", True, "Close time"),
        ColumnDef("cancel_comments", "STRING", True, "Cancel comments"),
        ColumnDef("created_at", "TIMESTAMP", False, "Record creation timestamp"),
    ]
)

DOOR_PRESSURE_SCHEMA = TableSchema(
    name="door_pressure",
    description="Service center door pressure (load planning) - dock door utilization metrics",
    source_system="PlanDoorPressure",
    primary_key=["pressure_id"],
    columns=[
        ColumnDef("pressure_id", "STRING", False, "Unique record identifier (UUID)"),
        ColumnDef("service_center", "STRING", False, "Service center code (RT)"),
        ColumnDef("flow_type", "STRING", True, "O/B (Outbound), I/B (Inbound), THROUGH"),
        ColumnDef("flow_type_order", "INT", True, "Sort order: 1=O/B, 2=I/B, 3=THROUGH"),
        ColumnDef("lp_date", "DATE", True, "Load plan date"),
        ColumnDef("ships", "DECIMAL(10,2)", True, "Shipment count (adjusted for through freight)"),
        ColumnDef("refresh_date", "TIMESTAMP", True, "Data refresh timestamp"),
        ColumnDef("created_at", "TIMESTAMP", False, "Record creation timestamp"),
    ]
)

DOOR_PARKING_COUNT_SCHEMA = TableSchema(
    name="door_parking_count",
    description="Service center door capacity reference table",
    source_system="Reference",
    primary_key=["service_center"],
    columns=[
        ColumnDef("service_center", "STRING", False, "Service center code"),
        ColumnDef("door_count", "INT", False, "Number of dock doors at terminal"),
        ColumnDef("effective_date", "DATE", True, "Effective date for door count"),
        ColumnDef("created_at", "TIMESTAMP", False, "Record creation timestamp"),
    ]
)


# =============================================================================
# Schema Registry
# =============================================================================

ALL_SCHEMAS: Dict[str, TableSchema] = {
    "customers": CUSTOMERS_SCHEMA,
    "agreements": AGREEMENTS_SCHEMA,
    "shippers": SHIPPERS_SCHEMA,
    "consignees": CONSIGNEES_SCHEMA,
    "shipments": SHIPMENTS_SCHEMA,
    "operations_events": OPERATIONS_EVENTS_SCHEMA,
    "transit_review": TRANSIT_REVIEW_SCHEMA,
    "pickups": PICKUPS_SCHEMA,
    "door_pressure": DOOR_PRESSURE_SCHEMA,
    "door_parking_count": DOOR_PARKING_COUNT_SCHEMA,
    "claims": CLAIMS_SCHEMA,
    "customer_revenue": CUSTOMER_REVENUE_SCHEMA,
    "features": FEATURES_SCHEMA,
    "predictions": PREDICTIONS_SCHEMA,
    "churn_events": CHURN_EVENTS_SCHEMA,
    "model_metrics": MODEL_METRICS_SCHEMA,
    "feature_importance": FEATURE_IMPORTANCE_SCHEMA,
    "policies": POLICIES_SCHEMA,
    "policy_cohorts": POLICY_COHORTS_SCHEMA,
}


def get_schema(table_name: str) -> TableSchema:
    """Get schema for a specific table."""
    if table_name not in ALL_SCHEMAS:
        raise ValueError(f"Unknown table: {table_name}. Available: {list(ALL_SCHEMAS.keys())}")
    return ALL_SCHEMAS[table_name]


def create_table_sql(schema: TableSchema) -> str:
    """
    Generate CREATE TABLE SQL statement for Fabric Lakehouse.
    
    Args:
        schema: TableSchema definition
        
    Returns:
        SQL CREATE TABLE statement
    """
    columns_sql = []
    for col in schema.columns:
        nullable = "" if col.nullable else " NOT NULL"
        comment = f" COMMENT '{col.description}'" if col.description else ""
        columns_sql.append(f"    {col.name} {col.data_type}{nullable}{comment}")
    
    columns_str = ",\n".join(columns_sql)
    
    source_comment = f"\n-- Source: {schema.source_system}" if schema.source_system else ""
    
    sql = f"""-- {schema.description}{source_comment}
CREATE TABLE IF NOT EXISTS {schema.name} (
{columns_str}
)
USING DELTA
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);"""
    
    return sql


def create_all_tables_sql() -> str:
    """Generate CREATE TABLE statements for all schemas."""
    statements = []
    for name, schema in ALL_SCHEMAS.items():
        statements.append(create_table_sql(schema))
    return "\n\n".join(statements)


def get_column_names(table_name: str) -> List[str]:
    """Get list of column names for a table."""
    schema = get_schema(table_name)
    return [col.name for col in schema.columns]


def get_required_columns(table_name: str) -> List[str]:
    """Get list of required (non-nullable) column names."""
    schema = get_schema(table_name)
    return [col.name for col in schema.columns if not col.nullable]


def get_source_tables() -> Dict[str, str]:
    """Get mapping of tables to their source systems."""
    return {name: schema.source_system for name, schema in ALL_SCHEMAS.items()}


# =============================================================================
# Source System Column Mapping Helpers
# =============================================================================

# FRP001 column mapping - update these to match your actual column names
FRP001_COLUMN_MAP = {
    "alpha_pro": "ALPHA_PRO_NUM",  # Adjust to actual column name
    "agreement_number": "AGREEMENT_NUM",
    "pickup_date": "PICKUP_DATE",
    "delivery_date": "DELIVERY_DATE",
    "scheduled_delivery_date": "SCHED_DELIVERY_DATE",
    "shipper_code": "SHIPPER_CODE",
    "consignee_code": "CONSIGNEE_CODE",
    "origin_service_center": "ORIG_SVC_CTR",
    "dest_service_center": "DEST_SVC_CTR",
    "weight": "WEIGHT",
    "pieces": "PIECES",
    "revenue": "REVENUE",
}

# TOP006 column mapping
TOP006_COLUMN_MAP = {
    "customer_code": "CUSTOMER_CODE",  # Adjust to actual column name
    "customer_name": "CUSTOMER_NAME",
    "segment": "SEGMENT",
    "industry": "INDUSTRY",
    "sales_rep": "SALES_REP",
    "region": "REGION",
}

# Claims Data column mapping
CLAIMS_COLUMN_MAP = {
    "claim_id": "Claim ID",
    "pro": "PRO",
    "claim_acknowledged_date": "Claim Acknowledged Date",
    "amount_filed": "$Filed",
    "amount_approved": "$Approved Amount",
    "amount_paid": "$Paid Amount",
    "claim_type": "Type Claim",
}

# TransitReview_V03 column mapping
TRANSIT_REVIEW_COLUMN_MAP = {
    "pro": "PRO",
    "pro_sfx": "PRO_SFX",
    "ori_id": "Ori ID",
    "dst_id": "Dst ID",
    "ori_zip": "ORI ZIP",
    "dst_zip": "DST ZIP",
    "pu_date": "PU DATE",
    "dlv_date": "DLV DATE",
    "dlv_date_adj": "DLV Date Adj",
    "original_edd": "ORIGINAL EDD",
    "est_delivery_date": "EST DELIVERY DATE",
    "anticipated_delvy_date": "ANTICIPATED DELVY DATE",
    "apt_date": "APT DATE",
    "agreement_number": "AGREEMENT NUMBER",
    "shipper_code": "SHIPPER CODE",
    "consignee_code": "CONSIGNEE CODE",
    "from_carrier": "FROM CARRIER",
    "to_carrier": "TO CARRIER",
    "std_trans_days": "STD TRANS DAYS",
    "added_days": "Added Days",
    "carrier_added_days": "CARRIER ADDED DAYS",
    "service_days": "SERVICE DAYS",
    "transit_days_overrun": "TRANSIT DAYS OVERRUN",
    "sign_for_overunder": "SIGN FOR OVERUNDER",
    "number_of_bring_backs": "NUMBER OF BRING BACKS",
    "hazardous_material_flag": "HAZARDOUS MATERIAL FLAG",
    "returned_flag": "RETURNED FLAG",
    "transit_time_code": "Service Codes",
    "all_short": "ALL SHORT",
    "misroute": "MISROUTE",
    "late_departure_lh": "Late Departure - LH",
    "late_arrival_lh": "Late Arrival - LH",
    "transit_failure_type": "Dispatch Transit Failure Codes",
    "customerid": "CUSTOMERID",
    "on_time_direct": "On Time - Direct",
    "late_sql_direct": "Late SQL - Direct",
}

# FMP030 Pickup column mapping
PICKUPS_COLUMN_MAP = {
    "service_center": "Service Center",
    "pku_region": "PKU Region",
    "pku_route": "PKU Route",
    "status_flag": "PKU Status Flag",
    "attempted": "PKU Attempted",
    "rescheduled": "PKU Rescheduled",
    "shipper_code": "Shipper Code",
    "shipper_name": "Shipper Name",
    "shipper_city": "Shipper City",
    "shipper_state": "Shipper State",
    "shipper_zip": "Shipper Zip Code",
    "country": "Country",
    "req_pku_date": "Req PKU Date",
    "driver_eid": "Driver EID",
    "cancel_reason": "Cancel Reason",
    "puhcantyp": "PUHCANTYP",
    "cancel_count": "CANCEL_COUNT",
    "comp_count": "COMP_COUNT",
    "stops": "Stops",
    "pu_request_number": "PU_REQUEST_NUMBER",
    "puh_create_type": "PUH_CREATE_TYPE",
    "entered_date": "ENTERED_DATE",
    "entered_time": "ENTERED_TIME",
    "sent_date": "SENT_DATE",
    "sent_time": "SENT_TIME",
    "cancel_date": "CANCEL_DATE",
    "cancel_time": "CANCEL_TIME",
    "pu_date": "PU_DATE",
    "pu_time": "PU_TIME",
    "close_date": "CLOSE_DATE",
    "close_time": "CLOSE_TIME",
    "cancel_comments": "Cancel Comment",
}

# Cancel reason code mapping for pickups
PICKUP_CANCEL_CODES = {
    "M": "Missed",          # Carrier fault - driver missed pickup
    "C": "Not Ready",       # Customer fault - freight not ready
    "A": "No Freight",      # Customer fault - no freight to pickup
    "R": "Duplicate",       # Exclude from metrics
    "O": "Other",           # Review case-by-case
}

# Door Pressure column mapping
DOOR_PRESSURE_COLUMN_MAP = {
    "service_center": "RT",
    "flow_type": "TYPE",
    "flow_type_order": "TYPE_ORDER",
    "lp_date": "LP_DATE",
    "ships": "SHIPS",
    "refresh_date": "REFRESH_DATE",
}


def get_source_column_map(source_system: str) -> Dict[str, str]:
    """Get column mapping for a source system."""
    maps = {
        "FRP001": FRP001_COLUMN_MAP,
        "TOP006": TOP006_COLUMN_MAP,
        "Claims Data": CLAIMS_COLUMN_MAP,
        "TransitReview_V03": TRANSIT_REVIEW_COLUMN_MAP,
        "FMP030": PICKUPS_COLUMN_MAP,
        "PlanDoorPressure": DOOR_PRESSURE_COLUMN_MAP,
    }
    return maps.get(source_system, {})


def get_cancel_reason_text(code: str) -> str:
    """Convert pickup cancel type code to readable text."""
    return PICKUP_CANCEL_CODES.get(code, "Unknown")

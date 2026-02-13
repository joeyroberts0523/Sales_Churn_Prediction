# Data Model: Customer Churn Prediction (LTL Freight)

**Version**: 2.0  
**Last Updated**: 2026-02-09  
**Platform**: Microsoft Fabric Lakehouse

## Overview

This data model supports churn prediction for LTL (Less-than-Truckload) freight customers using operational, claims, and revenue data.

## Entity Relationship Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    customers    │────<│   agreements    │────<│    shipments    │
│  (customer_code)│     │(agreement_number)│     │   (alpha_pro)   │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                        ┌────────────────────────────────┼────────────────────────────────┐
                        │                                │                                │
                        ▼                                ▼                                ▼
               ┌─────────────────┐              ┌─────────────────┐              ┌─────────────────┐
               │     claims      │              │ operations_events│              │    revenue      │
               │   (claim_id)    │              │   (alpha_pro)    │              │  (from TOP006)  │
               └─────────────────┘              └─────────────────┘              └─────────────────┘

┌─────────────────┐                    ┌─────────────────┐
│    shippers     │<───────────────────│    shipments    │
│ (shipper_code)  │                    │                 │
└─────────────────┘                    │                 │
                                       │                 │
┌─────────────────┐                    │                 │
│   consignees    │<───────────────────┘                 │
│(consignee_code) │                                      │
└─────────────────┘                                      │
```

## Source System Mapping

| Lakehouse Table | Source System | Key Fields |
|-----------------|---------------|------------|
| shipments | FRP001 | alpha_pro, agreement_number |
| transit_review | TransitReview_V03 | PRO, agreement_number |
| pickups | FMP030 (Pickup Header) | PU_REQUEST_NUMBER, shipper_number |
| door_pressure | PlanDoorPressure | service_center, lp_date |
| door_parking_count | Reference | service_center |
| cwi_compliance | CWIReporting.dbo.CWI_Compliance | pro_key |
| customers | TOP006 | customer_code |
| customer_revenue | TOP006 | customer_code, period |
| claims | Claims Data | claim_id, pro |
| operations_events | Transformed from transit_review + pickups | alpha_pro |
| shippers | Reference/Master Data | shipper_code |
| consignees | Reference/Master Data | consignee_code |

---

## Table Definitions

### 1. customers

**Source**: TOP006  
**Grain**: One row per customer  
**Purpose**: Master customer dimension

| Column | Type | Description | Source |
|--------|------|-------------|--------|
| customer_code | STRING | Primary key - customer identifier | TOP006 |
| customer_name | STRING | Customer business name | TOP006 |
| segment | STRING | Customer segment (e.g., National, Regional, SMB) | TOP006 |
| industry | STRING | Industry classification | TOP006 |
| start_date | DATE | Customer relationship start date | TOP006 |
| sales_rep | STRING | Assigned sales representative | TOP006 |
| region | STRING | Geographic region | TOP006 |
| is_active | BOOLEAN | Current active status | TOP006 |
| created_at | TIMESTAMP | Record creation timestamp | System |
| updated_at | TIMESTAMP | Last update timestamp | System |

**Primary Key**: customer_code

---

### 2. agreements

**Source**: Agreement/Contract system  
**Grain**: One row per agreement  
**Purpose**: Link customers to pricing agreements and shipment activity

| Column | Type | Description | Source |
|--------|------|-------------|--------|
| agreement_id | STRING | Unique agreement identifier (UUID) | System |
| agreement_number | STRING | Business agreement number | FRP001/Contract |
| customer_code | STRING | FK to customers | FRP001 |
| agreement_type | STRING | Type (Spot, Contract, Volume) | Contract |
| effective_date | DATE | Agreement start date | Contract |
| expiration_date | DATE | Agreement end date | Contract |
| status | STRING | Active, Expired, Cancelled | Contract |
| created_at | TIMESTAMP | Record creation timestamp | System |

**Primary Key**: agreement_id  
**Foreign Keys**: customer_code → customers.customer_code

---

### 3. shippers

**Source**: Master Data  
**Grain**: One row per shipper location  
**Purpose**: Shipper (origin) reference dimension

| Column | Type | Description | Source |
|--------|------|-------------|--------|
| shipper_code | STRING | Primary key - shipper identifier | Master Data |
| shipper_name | STRING | Shipper business name | Master Data |
| shipper_city | STRING | City | Master Data |
| shipper_state | STRING | State code | Master Data |
| shipper_zip | STRING | ZIP code | Master Data |
| customer_code | STRING | FK to customers (if shipper is the customer) | Master Data |
| created_at | TIMESTAMP | Record creation timestamp | System |

**Primary Key**: shipper_code

---

### 4. consignees

**Source**: Master Data  
**Grain**: One row per consignee location  
**Purpose**: Consignee (destination) reference dimension

| Column | Type | Description | Source |
|--------|------|-------------|--------|
| consignee_code | STRING | Primary key - consignee identifier | Master Data |
| consignee_name | STRING | Consignee business name | Master Data |
| consignee_city | STRING | City | Master Data |
| consignee_state | STRING | State code | Master Data |
| consignee_zip | STRING | ZIP code | Master Data |
| customer_code | STRING | FK to customers (if consignee is the customer) | Master Data |
| created_at | TIMESTAMP | Record creation timestamp | System |

**Primary Key**: consignee_code

---

### 5. shipments

**Source**: FRP001  
**Grain**: One row per PRO (shipment)  
**Purpose**: Shipment facts - core transactional data

| Column | Type | Description | Source |
|--------|------|-------------|--------|
| shipment_id | STRING | Unique ID (UUID) | System |
| alpha_pro | STRING | Alpha PRO number (primary business key) | FRP001 |
| agreement_number | STRING | FK to agreements | FRP001 |
| customer_code | STRING | FK to customers (denormalized for query performance) | FRP001/TOP006 |
| shipper_code | STRING | FK to shippers | FRP001 |
| consignee_code | STRING | FK to consignees | FRP001 |
| pickup_date | DATE | Scheduled/actual pickup date | FRP001 |
| delivery_date | DATE | Scheduled/actual delivery date | FRP001 |
| scheduled_delivery_date | DATE | Originally scheduled delivery | FRP001 |
| origin_service_center | STRING | Pickup service center code | FRP001 |
| dest_service_center | STRING | Delivery service center code | FRP001 |
| weight | DECIMAL(10,2) | Shipment weight (lbs) | FRP001 |
| pieces | INTEGER | Number of pieces | FRP001 |
| revenue | DECIMAL(12,2) | Shipment revenue | FRP001/TOP006 |
| created_at | TIMESTAMP | Record creation timestamp | System |

**Primary Key**: shipment_id  
**Business Key**: alpha_pro  
**Foreign Keys**: 
- agreement_number → agreements.agreement_number
- customer_code → customers.customer_code
- shipper_code → shippers.shipper_code
- consignee_code → consignees.consignee_code

---

### 6. operations_events

**Source**: Transformed from multiple operational tables  
**Grain**: One row per PRO (aggregated operational events)  
**Purpose**: Boolean flags for service failures + days late

| Column | Type | Description | Source |
|--------|------|-------------|--------|
| event_id | STRING | Unique ID (UUID) | System |
| alpha_pro | STRING | FK to shipments | Operational Tables |
| is_missed_pickup | BOOLEAN | Pickup was missed (True/False) | Transformed |
| is_late_delivery | BOOLEAN | Delivery was late (True/False) | Transformed |
| days_late | INTEGER | Number of days late (0 if on-time) | Transformed |
| is_cancelled_pickup | BOOLEAN | Pickup was cancelled (True/False) | Transformed |
| responsible_service_center | STRING | Service center responsible for issue | Transformed |
| event_date | DATE | Date of the primary event | Transformed |
| created_at | TIMESTAMP | Record creation timestamp | System |

**Primary Key**: event_id  
**Business Key**: alpha_pro  
**Foreign Keys**: alpha_pro → shipments.alpha_pro

**Transformation Logic**:
```sql
-- On-Time/Late from TransitReview_V03 (direct shipments only)
PROMISE_DATE = COALESCE(APT_DATE, EST_DELIVERY_DATE)
IS_LATE = DLV_DATE > PROMISE_DATE AND FROM_CARRIER = '' AND TO_CARRIER = ''
DAYS_LATE = DATEDIFF(DLV_DATE, PROMISE_DATE) WHERE POSITIVE, ELSE 0

-- From Pickup (FMP030)
-- PUHCANTYP codes:
--   'M' = Missed
--   'C' = Not Ready  
--   'A' = No Freight / Attempted
--   'R' = Duplicate
--   'O' = Other
IS_MISSED_PICKUP = PUHCANTYP = 'M'
IS_CANCELLED_PICKUP = CANCEL_COUNT = 1 AND PUHCANTYP NOT IN ('M', 'R')  -- excludes duplicates
CANCEL_REASON = CASE PUHCANTYP:
    'M' -> 'Missed'
    'C' -> 'Not Ready'
    'A' -> 'No Freight'
    'R' -> 'Duplicate'
    'O' -> 'Other'
```

---

### 7. transit_review

**Source**: TransitReview_V03 view  
**Grain**: One row per PRO + leg (filtered to relevant leg)  
**Purpose**: Transit performance metrics - on-time, late, days overrun

| Column | Type | Description | Source |
|--------|------|-------------|--------|
| pro | STRING | PRO number | TransitReview.PRO |
| pro_sfx | STRING | PRO suffix | TransitReview.PRO_SFX |
| ori_id | STRING | Origin service center | TransitReview.ORI |
| dst_id | STRING | Destination service center | TransitReview.DST |
| ori_zip | STRING | Origin ZIP | TransitReview.ORI_ZIP |
| dst_zip | STRING | Destination ZIP | TransitReview.DST_ZIP |
| pu_date | DATE | Pickup date | TransitReview.PU_DATE |
| dlv_date | DATE | Actual delivery date | TransitReview.DLV_DATE |
| original_edd | DATE | Original estimated delivery | TransitReview.ORIGINAL_EDD |
| est_delivery_date | DATE | Estimated delivery date | TransitReview.EST_DELIVERY_DATE |
| apt_date | DATE | Appointment date (if set) | TransitReview.APT_DATE |
| agreement_number | STRING | Agreement number | TransitReview.AGREEMENT_NUMBER |
| shipper_code | STRING | Shipper code | TransitReview.SHIPPER_CODE |
| consignee_code | STRING | Consignee code | TransitReview.CONSIGNEE_CODE |
| from_carrier | STRING | Interline from carrier | TransitReview.FROM_CARRIER |
| to_carrier | STRING | Interline to carrier | TransitReview.TO_CARRIER |
| std_trans_days | INTEGER | Standard transit days | TransitReview.STD_TRANS_DAYS |
| added_days | INTEGER | Added days | TransitReview.ADDED_DAYS |
| service_days | INTEGER | Service days | TransitReview.SERVICE_DAYS |
| transit_days_overrun | INTEGER | Days over standard transit | TransitReview.TRANSIT_DAYS_OVERRUN |
| number_of_bring_backs | INTEGER | Bring-back attempts | TransitReview.NUMBER_OF_BRING_BACKS |
| transit_failure_type | STRING | Failure type code | TransitReview.TRANSIT_FAILURE_TYPE |
| on_time_direct | BOOLEAN | On-time (direct only) | Calculated: see below |
| late_sql_direct | BOOLEAN | Late (direct only) | Calculated: see below |
| is_intra | BOOLEAN | Intra-terminal (ORI=DST) | Calculated |
| is_intl | BOOLEAN | International shipment | Calculated |

**Calculated Fields**:
```sql
PROMISE_DATE = COALESCE(APT_DATE, EST_DELIVERY_DATE)
ON_TIME_DIRECT = FROM_CARRIER = '' AND TO_CARRIER = '' AND PROMISE_DATE >= DLV_DATE
LATE_SQL_DIRECT = FROM_CARRIER = '' AND TO_CARRIER = '' AND DLV_DATE > PROMISE_DATE
IS_INTRA = ORI = DST
IS_INTL = FROM_CARRIER <> '' OR TO_CARRIER <> ''
```

**Primary Key**: (pro, leg_sequence) - or use row ID  
**Business Key**: pro  

---

### 8. pickups

**Source**: FMP030 (Pickup Header) via openquery  
**Grain**: One row per pickup request  
**Purpose**: Pickup request outcomes - completed, missed, cancelled, not ready

| Column | Type | Description | Source |
|--------|------|-------------|--------|
| pu_request_number | STRING | Pickup request ID (PK) | FMP030.PUH_PU_REQUEST_NUMBER |
| service_center | STRING | Pickup terminal | FMP030.PKU_TERMINAL |
| pku_region | STRING | Region | FMP030.PKU_REGION |
| pku_route | STRING | Pickup route | FMP030.PKU_ROUTE_NAME |
| status_flag | STRING | PKU or CAN | FMP030.PUH_STATUS |
| attempted | STRING | 'Y' if attempted | Derived from PUHCANTYP='A' |
| rescheduled | STRING | Rescheduled flag | FMP030.PUH_RESCHEDUL_FLAG |
| shipper_code | STRING | Shipper number | FMP030.PUH_SHIPPER_NUMBER |
| shipper_name | STRING | Shipper name | FMP030.PUH_SHIPPER_NAME |
| shipper_city | STRING | City | FMP030.PUH_SHIPPER_CITY |
| shipper_state | STRING | State | FMP030.PUH_SHIPPER_STATE |
| shipper_zip | STRING | ZIP code | FMP030.PUH_SHIPPER_ZIPCODE |
| req_pku_date | DATE | Requested pickup date | FMP030.PUH_APPOINTMENT_DATE |
| driver_eid | STRING | Driver ID | FMP030.PUH_PICKUP_DRVR |
| cancel_reason | STRING | Cancel reason text | Derived - see codes |
| puhcantyp | STRING | Cancel type code (M/C/A/R/O) | FMP030.PUHCANTYP |
| cancel_count | INTEGER | 1 if cancelled, 0 if completed | Calculated |
| comp_count | INTEGER | 1 if completed, 0 if cancelled | Calculated |
| cancel_date | DATE | Cancellation date | FMP030.PUH_CANCEL_DATE |
| cancel_time | TIME | Cancellation time | FMP030.PUH_CANCEL_TIME |
| cancel_comments | STRING | Cancel comments | FMP030.PUH_CANCEL_REASON |
| pu_date | DATE | Actual pickup date | FMP030.PUH_PICKUP_DATE |
| pu_time | TIME | Actual pickup time | FMP030.PUH_PICKUP_TIME |

**Cancel Reason Codes (PUHCANTYP)**:
| Code | Meaning | Category |
|------|---------|----------|
| M | Missed | Not Completed - Carrier Fault |
| C | Not Ready | Not Completed - Customer Fault |
| A | No Freight | Not Completed - Customer Fault |
| R | Duplicate | Exclude from metrics |
| O | Other | Review case-by-case |
| STATUS='PKU' | Completed Pickup | Completed |
| DRIVER CANCEL | Driver cancelled | Not Completed - Carrier Fault |
| TIME EXPIRED | Timed out | Not Completed - System |

**Primary Key**: pu_request_number  
**Business Key**: (shipper_code, req_pku_date)  

---

### 9. door_pressure

**Source**: PlanDoorPressure view  
**Grain**: One row per service center per flow type per date  
**Purpose**: Service center dock door utilization - capacity pressure metrics

| Column | Type | Description | Source |
|--------|------|-------------|--------|
| pressure_id | STRING | Unique ID (UUID) | System |
| service_center | STRING | Service center code | PlanDoorPressure.RT |
| flow_type | STRING | O/B (Outbound), I/B (Inbound), THROUGH | PlanDoorPressure.TYPE |
| flow_type_order | INTEGER | Sort order: 1=O/B, 2=I/B, 3=THROUGH | PlanDoorPressure.TYPE_ORDER |
| lp_date | DATE | Load plan date | PlanDoorPressure.LP_DATE |
| ships | DECIMAL(10,2) | Shipment count (adjusted for through) | PlanDoorPressure.SHIPS |
| refresh_date | TIMESTAMP | Data refresh timestamp | PlanDoorPressure.REFRESH_DATE |

**Primary Key**: pressure_id  
**Business Key**: (service_center, flow_type, lp_date)

**Pressure Calculation**:
```
Door Pressure = Ships / (MaxDoorCount × WorkingDays)

Where:
- Ships: Sum from door_pressure table
- MaxDoorCount: From door_parking_count reference
- WorkingDays: Count of working days in period
```

Higher pressure indicates a more congested terminal, potentially correlating with service issues.

---

### 10. door_parking_count

**Source**: Reference/Configuration  
**Grain**: One row per service center  
**Purpose**: Service center dock door capacity reference

| Column | Type | Description | Source |
|--------|------|-------------|--------|
| service_center | STRING | Service center code (PK) | Reference |
| door_count | INTEGER | Number of dock doors at terminal | Configuration |
| effective_date | DATE | Effective date for door count | Configuration |

**Primary Key**: service_center

---

### 11. cwi_compliance

**Source**: CWIReporting.dbo.CWI_Compliance  
**Grain**: One row per PRO inspected  
**Purpose**: Catch Weight Inspection (reweigh/reclassification) compliance tracking

CWI is the inspection program that verifies customer-declared weights and freight classes. 
High flagged rates indicate discrepancies → unexpected billing adjustments → potential disputes.

| Column | Type | Description | Source |
|--------|------|-------------|--------|
| pro | STRING | Alpha PRO number | ALPHA_PRO_NUMBER |
| pro_suffix | STRING | PRO suffix (blank or MR) | ALPHA_PRO_SUFFIX |
| pro_key | STRING | PRO-Suffix concatenated key (PK) | Derived |
| pickup_date | DATE | Pickup date | PU_Date |
| delivery_date | DATE | Delivery date | DELIVERY_DATE8 (converted) |
| target_type | STRING | D=Delivery, W=Weight inspection | TARGETTYPE |
| pl_term | STRING | Terminal where inspection occurred | PLTERM → FRP015 |
| pl_emp_id | STRING | Employee ID who performed inspection | PLEMPID |
| pl_touches | INTEGER | Number of inspection touches | PL_Touches |
| selected | INTEGER | 1=Selected for inspection (event capable) | Selected AND Event_Capable |
| flagged | INTEGER | 1=Flagged for weight/class discrepancy | Flagged |
| event | INTEGER | 1=Inspection event occurred | EVENT_TIMESTAMP IS NOT NULL |
| ignore | INTEGER | 1=Ignored (IG or reasonableness check) | IG_Event OR EVENT_PROCESS_CODE='IG' OR Reasonableness_Check |
| event_complete | INTEGER | 1=Inspection completed | Event_Complete |
| additional_event | INTEGER | 1=Unselected PRO with event (extra) | Selected=0 AND EVENT_TIMESTAMP IS NOT NULL |

**Primary Key**: pro_key

**Key Metrics**:
- Flagged Rate = Flagged / Events → High rate indicates billing discrepancy risk
- Completed Rate = Event_Complete / Events → Compliance tracking

---

### 12. claims

**Source**: Claims Data table  
**Grain**: One row per claim  
**Purpose**: Claims filed against shipments

| Column | Type | Description | Source |
|--------|------|-------------|--------|
| claim_id | STRING | Primary key - claim identifier | Claims Data |
| pro | STRING | PRO number (FK to shipments.alpha_pro) | Claims Data |
| customer_code | STRING | FK to customers (denormalized) | Derived |
| claim_acknowledged_date | DATE | Date claim was acknowledged | Claims Data |
| amount_filed | DECIMAL(12,2) | Dollar amount filed | Claims Data.$Filed |
| amount_approved | DECIMAL(12,2) | Dollar amount approved | Claims Data.$Approved Amount |
| amount_paid | DECIMAL(12,2) | Dollar amount paid | Claims Data.$Paid Amount |
| claim_type | STRING | Type of claim (Damage, Loss, Shortage, etc.) | Claims Data.Type Claim |
| claim_status | STRING | Current status (Open, Paid, Denied, etc.) | Derived |
| created_at | TIMESTAMP | Record creation timestamp | System |

**Primary Key**: claim_id  
**Foreign Keys**: 
- pro → shipments.alpha_pro
- customer_code → customers.customer_code

---

### 8. customer_revenue

**Source**: TOP006  
**Grain**: One row per customer per period (monthly)  
**Purpose**: Revenue aggregation for trend analysis

| Column | Type | Description | Source |
|--------|------|-------------|--------|
| revenue_id | STRING | Unique ID (UUID) | System |
| customer_code | STRING | FK to customers | TOP006 |
| period_date | DATE | First day of month | TOP006 |
| period_type | STRING | 'MONTHLY' or 'WEEKLY' | System |
| shipment_count | INTEGER | Number of shipments in period | Aggregated |
| total_revenue | DECIMAL(14,2) | Total revenue in period | TOP006 |
| total_weight | DECIMAL(14,2) | Total weight shipped | Aggregated |
| avg_revenue_per_shipment | DECIMAL(10,2) | Average revenue per shipment | Calculated |
| created_at | TIMESTAMP | Record creation timestamp | System |

**Primary Key**: revenue_id  
**Foreign Keys**: customer_code → customers.customer_code

---

### 9. features

**Grain**: One row per customer per scoring date  
**Purpose**: Computed features for ML model input

| Column | Type | Description |
|--------|------|-------------|
| feature_id | STRING | Unique ID (UUID) |
| customer_code | STRING | FK to customers |
| feature_set_id | STRING | Version identifier (e.g., "v1_20260209") |
| computed_date | DATE | Date features were calculated |
| **Tenure Features** | | |
| tenure_days | INTEGER | Days since first shipment |
| tenure_months | INTEGER | Months since first shipment |
| **Activity Features** | | |
| shipment_count_30d | INTEGER | Shipments in last 30 days |
| shipment_count_60d | INTEGER | Shipments in last 60 days |
| shipment_count_90d | INTEGER | Shipments in last 90 days |
| days_since_last_shipment | INTEGER | Recency |
| **Revenue Features** | | |
| revenue_30d | DECIMAL(12,2) | Revenue last 30 days |
| revenue_60d | DECIMAL(12,2) | Revenue last 60 days |
| revenue_90d | DECIMAL(12,2) | Revenue last 90 days |
| revenue_trend | DECIMAL(8,4) | Revenue change (recent vs prior period) |
| avg_revenue_per_shipment | DECIMAL(10,2) | Average revenue per shipment |
| **Operations Features** | | |
| missed_pickup_count_90d | INTEGER | Missed pickups in 90 days |
| late_delivery_count_90d | INTEGER | Late deliveries in 90 days |
| cancelled_pickup_count_90d | INTEGER | Cancelled pickups in 90 days |
| avg_days_late_90d | DECIMAL(6,2) | Average days late in 90 days |
| missed_pickup_rate | DECIMAL(6,4) | % of shipments with missed pickup |
| late_delivery_rate | DECIMAL(6,4) | % of shipments delivered late |
| on_time_delivery_rate | DECIMAL(6,4) | % of shipments on-time |
| **Interline Features** | | |
| interline_count_90d | INTEGER | Interline shipments in 90 days |
| interline_pct | DECIMAL(6,4) | % of shipments that are interline |
| **Claims Features** | | |
| claim_count_90d | INTEGER | Claims in last 90 days |
| claim_count_365d | INTEGER | Claims in last year |
| total_claims_filed_90d | DECIMAL(12,2) | $ claims filed in 90 days |
| total_claims_paid_90d | DECIMAL(12,2) | $ claims paid in 90 days |
| claim_rate | DECIMAL(6,4) | Claims per shipment |
| avg_claim_amount | DECIMAL(10,2) | Average claim amount |
| **Service Center Features** | | |
| distinct_service_centers | INTEGER | Number of service centers used |
| primary_service_center | STRING | Most frequent service center |
| service_center_issue_rate | DECIMAL(6,4) | % issues at primary center |
| **Door Pressure Features** | | |
| primary_sc_avg_pressure | DECIMAL(6,4) | Average door pressure at primary SC (90d) |
| primary_sc_max_pressure | DECIMAL(6,4) | Peak door pressure at primary SC (90d) |
| high_pressure_shipment_pct | DECIMAL(6,4) | % of shipments during high-pressure days |
| weighted_pressure_exposure | DECIMAL(6,4) | Ship-weighted average pressure exposure |
| **Shipper/Consignee Features** | | |
| distinct_shippers | INTEGER | Number of unique shippers |
| distinct_consignees | INTEGER | Number of unique consignees |
| top_lane_concentration | DECIMAL(6,4) | % volume in top shipper-consignee lane |
| **Lane Abandonment Features** | | |
| lanes_abandoned_90d | INTEGER | Lanes with shipments 90-180d ago but 0 in last 90d |
| lanes_abandoned_pct | DECIMAL(6,4) | % of historical lanes that were abandoned |
| new_lanes_90d | INTEGER | New lanes started in last 90 days |
| lane_churn_rate | DECIMAL(6,4) | Net lane change rate: (new - abandoned) / total historical |
| **CWI Compliance Features** | | |
| cwi_inspections_90d | INTEGER | CWI inspection events in 90 days |
| cwi_flagged_90d | INTEGER | Shipments flagged for weight/class discrepancy |
| cwi_flagged_rate | DECIMAL(6,4) | % of inspections flagged (billing risk indicator) |
| cwi_touches_90d | INTEGER | Total inspection touches in 90 days |
| cwi_completed_rate | DECIMAL(6,4) | % of inspections completed |
| created_at | TIMESTAMP | Record creation timestamp |

**Primary Key**: feature_id

---

### 14. predictions

**Grain**: One row per customer per churn bucket per prediction date  
**Purpose**: Model prediction outputs

| Column | Type | Description |
|--------|------|-------------|
| prediction_id | STRING | Unique ID (UUID) |
| customer_code | STRING | FK to customers |
| prediction_date | DATE | Date prediction was generated |
| model_version | STRING | Model version identifier |
| churn_bucket | STRING | 'churn_30d', 'churn_60d', 'churn_90d', 'revenue_decline' |
| churn_probability | DECIMAL(6,4) | Predicted probability (0.0-1.0) |
| risk_tier | STRING | 'Low', 'Medium', 'High', 'Critical' |
| previous_probability | DECIMAL(6,4) | Last week's probability |
| probability_change | DECIMAL(6,4) | Week-over-week change |
| alert_triggered | BOOLEAN | True if crossed risk threshold |
| created_at | TIMESTAMP | Record creation timestamp |

**Primary Key**: prediction_id

---

### 11. churn_events

**Grain**: One row per churn event  
**Purpose**: Actual churn outcomes for model training/validation

| Column | Type | Description |
|--------|------|-------------|
| churn_event_id | STRING | Unique ID (UUID) |
| customer_code | STRING | FK to customers |
| event_date | DATE | Date churn was identified |
| churn_type | STRING | 'inactivity_30d', 'inactivity_60d', 'inactivity_90d', 'revenue_decline', 'contract_cancellation' |
| revenue_at_churn | DECIMAL(12,2) | Last period revenue before churn |
| shipments_at_churn | INTEGER | Last period shipment count |
| created_at | TIMESTAMP | Record creation timestamp |

**Primary Key**: churn_event_id

---

## Churn Definitions for LTL Freight

| Bucket | Definition | Business Logic |
|--------|------------|----------------|
| churn_30d | No shipments in >30 days | `days_since_last_shipment > 30` |
| churn_60d | No shipments in >60 days | `days_since_last_shipment > 60` |
| churn_90d | No shipments in >90 days | `days_since_last_shipment > 90` |
| revenue_decline | Revenue dropped >50% vs prior period | `revenue_trend < -0.50` |
| contract_cancellation | Agreement status = 'Cancelled' | Explicit event |

---

## Key Joins

### Customer → Shipments (via Agreement)
```sql
SELECT c.*, s.*
FROM customers c
JOIN agreements a ON c.customer_code = a.customer_code
JOIN shipments s ON a.agreement_number = s.agreement_number
```

### Shipment → Operations + Claims
```sql
SELECT s.*, o.*, cl.*
FROM shipments s
LEFT JOIN operations_events o ON s.alpha_pro = o.alpha_pro
LEFT JOIN claims cl ON s.alpha_pro = cl.pro
```

### Full Customer View
```sql
SELECT 
    c.customer_code,
    c.customer_name,
    COUNT(DISTINCT s.alpha_pro) as total_shipments,
    SUM(s.revenue) as total_revenue,
    SUM(CASE WHEN o.is_late_delivery THEN 1 ELSE 0 END) as late_deliveries,
    COUNT(DISTINCT cl.claim_id) as total_claims
FROM customers c
LEFT JOIN agreements a ON c.customer_code = a.customer_code
LEFT JOIN shipments s ON a.agreement_number = s.agreement_number
LEFT JOIN operations_events o ON s.alpha_pro = o.alpha_pro
LEFT JOIN claims cl ON s.alpha_pro = cl.pro
GROUP BY c.customer_code, c.customer_name
```

---

## Data Quality Rules

| Table | Rule | Severity |
|-------|------|----------|
| shipments | alpha_pro must be unique | ERROR |
| shipments | pickup_date <= delivery_date | WARNING |
| operations_events | days_late >= 0 | ERROR |
| claims | amount_paid <= amount_filed | WARNING |
| customers | customer_code not null | ERROR |
| customer_revenue | total_revenue >= 0 | ERROR |

---

## Notes

1. **PRO Number**: Alpha PRO is the primary identifier for shipments in LTL freight
2. **Customer vs Shipper/Consignee**: Customer is the billing entity; shipper/consignee are physical locations
3. **Denormalization**: customer_code duplicated on shipments/claims for query performance
4. **Revenue Attribution**: Revenue tracked at shipment level, aggregated to customer monthly
5. **Service Center**: Track which terminal is responsible for service failures

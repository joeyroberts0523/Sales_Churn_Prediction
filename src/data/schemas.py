"""
Delta Table Schema Definitions for Microsoft Fabric Lakehouse.

This module defines the schemas for all Delta tables used in the
churn prediction project. These schemas are used for:
- Creating tables in Fabric Lakehouse
- Validating data before writing
- Documentation reference

Use create_tables_sql() to generate Create Table statements for Fabric.
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
    description: str = ""


# =============================================================================
# Table Schemas per data-model.md
# =============================================================================

CUSTOMERS_SCHEMA = TableSchema(
    name="customers",
    description="Customer master data with demographic and account information",
    primary_key=["customer_id"],
    columns=[
        ColumnDef("customer_id", "STRING", False, "Unique customer identifier"),
        ColumnDef("customer_name", "STRING", True, "Customer display name"),
        ColumnDef("email", "STRING", True, "Contact email address"),
        ColumnDef("segment", "STRING", True, "Customer segment (e.g., Enterprise, SMB, Consumer)"),
        ColumnDef("region", "STRING", True, "Geographic region"),
        ColumnDef("industry", "STRING", True, "Industry classification"),
        ColumnDef("start_date", "DATE", True, "Date customer relationship began"),
        ColumnDef("contract_type", "STRING", True, "Contract type (Monthly, Annual, Multi-year)"),
        ColumnDef("contract_value", "DECIMAL(18,2)", True, "Annual contract value"),
        ColumnDef("is_active", "BOOLEAN", True, "Whether customer is currently active"),
        ColumnDef("created_at", "TIMESTAMP", False, "Record creation timestamp"),
        ColumnDef("updated_at", "TIMESTAMP", False, "Record last update timestamp"),
    ]
)

CUSTOMER_ACTIVITY_SCHEMA = TableSchema(
    name="customer_activity",
    description="Customer interaction and activity events",
    primary_key=["activity_id"],
    columns=[
        ColumnDef("activity_id", "STRING", False, "Unique activity identifier"),
        ColumnDef("customer_id", "STRING", False, "Reference to customers table"),
        ColumnDef("activity_date", "TIMESTAMP", False, "When the activity occurred"),
        ColumnDef("activity_type", "STRING", False, "Type of activity (login, purchase, support, etc.)"),
        ColumnDef("activity_channel", "STRING", True, "Channel (web, mobile, api, phone)"),
        ColumnDef("activity_value", "DECIMAL(18,2)", True, "Monetary value if applicable"),
        ColumnDef("activity_details", "STRING", True, "Additional activity metadata (JSON)"),
        ColumnDef("created_at", "TIMESTAMP", False, "Record creation timestamp"),
    ]
)

CHURN_EVENTS_SCHEMA = TableSchema(
    name="churn_events",
    description="Explicit churn and cancellation events",
    primary_key=["churn_event_id"],
    columns=[
        ColumnDef("churn_event_id", "STRING", False, "Unique churn event identifier"),
        ColumnDef("customer_id", "STRING", False, "Reference to customers table"),
        ColumnDef("churn_date", "DATE", False, "Date of churn/cancellation"),
        ColumnDef("churn_type", "STRING", False, "Type: explicit (cancellation) or inferred (inactivity)"),
        ColumnDef("churn_reason", "STRING", True, "Reason for churn if provided"),
        ColumnDef("churn_reason_category", "STRING", True, "Categorized reason (price, competitor, etc.)"),
        ColumnDef("feedback_score", "INT", True, "Exit survey score if available"),
        ColumnDef("created_at", "TIMESTAMP", False, "Record creation timestamp"),
    ]
)

FEATURES_SCHEMA = TableSchema(
    name="features",
    description="Pre-computed feature vectors for model training and scoring",
    primary_key=["feature_id"],
    columns=[
        ColumnDef("feature_id", "STRING", False, "Unique feature record identifier"),
        ColumnDef("customer_id", "STRING", False, "Reference to customers table"),
        ColumnDef("feature_set_id", "STRING", False, "Version identifier for feature set"),
        ColumnDef("computed_date", "DATE", False, "Date features were computed"),
        ColumnDef("tenure_days", "INT", True, "Days since customer start date"),
        ColumnDef("days_since_last_activity", "INT", True, "Days since most recent activity"),
        ColumnDef("total_activities", "INT", True, "Total number of activity events"),
        ColumnDef("activity_frequency", "DECIMAL(10,4)", True, "Activities per month"),
        ColumnDef("purchase_count", "INT", True, "Number of purchase events"),
        ColumnDef("purchase_total", "DECIMAL(18,2)", True, "Total purchase value"),
        ColumnDef("support_ticket_count", "INT", True, "Number of support tickets"),
        ColumnDef("login_count_30d", "INT", True, "Logins in last 30 days"),
        ColumnDef("login_count_60d", "INT", True, "Logins in last 60 days"),
        ColumnDef("login_count_90d", "INT", True, "Logins in last 90 days"),
        ColumnDef("feature_json", "STRING", True, "Additional features as JSON"),
        ColumnDef("created_at", "TIMESTAMP", False, "Record creation timestamp"),
    ]
)

PREDICTIONS_SCHEMA = TableSchema(
    name="predictions",
    description="Model prediction outputs for all customers",
    primary_key=["prediction_id"],
    columns=[
        ColumnDef("prediction_id", "STRING", False, "Unique prediction identifier"),
        ColumnDef("customer_id", "STRING", False, "Reference to customers table"),
        ColumnDef("prediction_date", "DATE", False, "Date prediction was generated"),
        ColumnDef("model_version", "STRING", False, "Model version used for prediction"),
        ColumnDef("churn_bucket", "STRING", False, "Churn bucket (30d, 60d, 90d, explicit)"),
        ColumnDef("churn_probability", "DECIMAL(5,4)", False, "Probability of churn (0-1)"),
        ColumnDef("risk_tier", "STRING", False, "Risk classification (Low, Medium, High, Critical)"),
        ColumnDef("previous_probability", "DECIMAL(5,4)", True, "Previous week probability"),
        ColumnDef("probability_change", "DECIMAL(5,4)", True, "Week-over-week change"),
        ColumnDef("alert_triggered", "BOOLEAN", True, "Whether risk alert was triggered"),
        ColumnDef("created_at", "TIMESTAMP", False, "Record creation timestamp"),
    ]
)

MODEL_METRICS_SCHEMA = TableSchema(
    name="model_metrics",
    description="Model performance metrics for tracking and comparison",
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
        ColumnDef("ci_lower", "DECIMAL(10,6)", True, "95% confidence interval lower bound"),
        ColumnDef("ci_upper", "DECIMAL(10,6)", True, "95% confidence interval upper bound"),
        ColumnDef("importance_rank", "INT", False, "Rank by absolute coefficient"),
        ColumnDef("is_significant", "BOOLEAN", True, "Whether p_value < 0.05"),
        ColumnDef("created_at", "TIMESTAMP", False, "Record creation timestamp"),
    ]
)

POLICIES_SCHEMA = TableSchema(
    name="policies",
    description="Retention policies and interventions",
    primary_key=["policy_id"],
    columns=[
        ColumnDef("policy_id", "STRING", False, "Unique policy identifier"),
        ColumnDef("policy_name", "STRING", False, "Display name for policy"),
        ColumnDef("policy_type", "STRING", False, "Type (discount, outreach, feature, etc.)"),
        ColumnDef("description", "STRING", True, "Detailed policy description"),
        ColumnDef("start_date", "DATE", False, "Policy effective start date"),
        ColumnDef("end_date", "DATE", True, "Policy end date (null if ongoing)"),
        ColumnDef("target_segment", "STRING", True, "Target customer segment"),
        ColumnDef("target_risk_tier", "STRING", True, "Target risk tier (High, Critical)"),
        ColumnDef("is_active", "BOOLEAN", True, "Whether policy is currently active"),
        ColumnDef("created_at", "TIMESTAMP", False, "Record creation timestamp"),
        ColumnDef("updated_at", "TIMESTAMP", False, "Record last update timestamp"),
    ]
)

POLICY_COHORTS_SCHEMA = TableSchema(
    name="policy_cohorts",
    description="Customer assignments to policy treatment and control groups",
    primary_key=["cohort_id"],
    columns=[
        ColumnDef("cohort_id", "STRING", False, "Unique cohort assignment identifier"),
        ColumnDef("policy_id", "STRING", False, "Reference to policies table"),
        ColumnDef("customer_id", "STRING", False, "Reference to customers table"),
        ColumnDef("cohort_type", "STRING", False, "treatment or control"),
        ColumnDef("assignment_date", "DATE", False, "Date customer was assigned to cohort"),
        ColumnDef("risk_score_at_assignment", "DECIMAL(5,4)", True, "Churn probability when assigned"),
        ColumnDef("outcome_measured", "BOOLEAN", True, "Whether outcome has been measured"),
        ColumnDef("outcome_date", "DATE", True, "Date outcome was measured"),
        ColumnDef("did_churn", "BOOLEAN", True, "Whether customer churned (outcome)"),
        ColumnDef("created_at", "TIMESTAMP", False, "Record creation timestamp"),
    ]
)


# =============================================================================
# Schema Registry
# =============================================================================

ALL_SCHEMAS: Dict[str, TableSchema] = {
    "customers": CUSTOMERS_SCHEMA,
    "customer_activity": CUSTOMER_ACTIVITY_SCHEMA,
    "churn_events": CHURN_EVENTS_SCHEMA,
    "features": FEATURES_SCHEMA,
    "predictions": PREDICTIONS_SCHEMA,
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
    
    sql = f"""-- {schema.description}
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

import os
from pydantic import BaseModel

class Settings(BaseModel):
    gcp_project: str = os.getenv("GCP_PROJECT", "")
    bq_dataset: str = os.getenv("BQ_DATASET", "infra_gestion")
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "354063050046-fkp06ao8aauems1gcj4hlngljf56o3cj.apps.googleusercontent.com")
    allow_insecure_local: bool = os.getenv("ALLOW_INSECURE_LOCAL", "true").lower() == "true"

settings = Settings()

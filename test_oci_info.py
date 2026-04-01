import os
from dotenv import load_dotenv

load_dotenv()

print("OCI_REGION =", os.getenv("OCI_REGION"))
print("OCI_COMPARTMENT_ID =", os.getenv("OCI_COMPARTMENT_ID"))
print("OCI_MODEL_ID =", os.getenv("OCI_MODEL_ID"))

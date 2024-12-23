from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from phonenumbers import carrier, parse, is_valid_number, NumberParseException
import random
import csv
from typing import List
from fastapi.responses import FileResponse
import os
import shutil
import uvicorn
from pydantic import BaseModel

app = FastAPI()

# Enable CORS for all domains (adjust for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure there's a folder for generated files (change path as needed)
GENERATED_FILES_PATH = "generated_files"
if not os.path.exists(GENERATED_FILES_PATH):
    os.makedirs(GENERATED_FILES_PATH)

# Function to generate a random phone number with a given country code
def generate_phone_number(country_code: str, prefix: str):
    random_number = random.randint(1000000, 9999999)  # Generate a 7-digit number
    phone_number = f"{country_code}{prefix}{random_number}"
    return phone_number

# Function to check if the phone number is valid
def is_valid_phone_number(phone_number: str, country_code: str):
    try:
        parsed_number = parse(phone_number, country_code)
        return is_valid_number(parsed_number)
    except NumberParseException:
        return False

# Function to get the carrier of a phone number
def get_carrier(phone_number: str, country_code: str):
    try:
        parsed_number = parse(phone_number, country_code)
        carrier_name = carrier.name_for_number(parsed_number, "en")
        return carrier_name if carrier_name != "Unknown" else None
    except Exception as e:
        print(f"Error in carrier lookup: {e}")
        return None

# Generate phone numbers and validate them
def generate_phone_numbers(country_code: str, prefix: str, amount: int):
    valid_numbers = []
    for _ in range(amount):
        phone_number = generate_phone_number(country_code, prefix)
        if is_valid_phone_number(phone_number, country_code):
            carrier_name = get_carrier(phone_number, country_code)
            if carrier_name:
                valid_numbers.append({"phone_number": phone_number, "carrier": carrier_name})
    return valid_numbers

# Background task to save phone numbers to a CSV file
def save_to_csv(file_path: str, numbers: List[dict]):
    with open(file_path, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Phone Number", "Carrier"])
        for item in numbers:
            writer.writerow([item["phone_number"], item["carrier"]])

# Endpoint to generate phone numbers and provide a download link for the CSV
class PhoneNumberRequest(BaseModel):
    country_code: str
    prefix: str
    amount: int

@app.post("/generate-and-download")
async def generate_and_download(request: PhoneNumberRequest, background_tasks: BackgroundTasks):
    if not request.country_code.startswith("+"):
        raise HTTPException(status_code=400, detail="Country code must start with '+'")
    if not request.prefix.isdigit() or len(request.prefix) < 3:
        raise HTTPException(status_code=400, detail="Prefix must be a number with at least 3 digits")
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")
    
    valid_numbers = generate_phone_numbers(request.country_code, request.prefix, request.amount)
    
    # Ensure the file is saved in the correct directory
    file_path = os.path.join(GENERATED_FILES_PATH, "generated_phone_numbers.csv")
    
    background_tasks.add_task(save_to_csv, file_path, valid_numbers)
    
    download_link = f"/download-csv?file_path={file_path}"
    return {"detail": "CSV generation in progress", "download_link": download_link}

# Endpoint to download the CSV file
@app.get("/download-csv")
async def download_csv(file_path: str):
    # Check if the file exists before attempting to serve it
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type='text/csv', filename='phone_numbers.csv')
    else:
        raise HTTPException(status_code=404, detail="File not found")

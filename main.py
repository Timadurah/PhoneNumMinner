from fastapi import FastAPI, HTTPException, BackgroundTasks
from phonenumbers import carrier, parse, is_valid_number, NumberParseException
import random
import csv
from typing import List
import uvicorn

app = FastAPI()

# Function to generate a random phone number with a given country code
def generate_phone_number(country_code: str, prefix: str):
    random_number = random.randint(1000000, 9999999)  # Generate a 7-digit number
    phone_number = f"{country_code}{prefix}{random_number}"  # Combine with country code and prefix
    return phone_number

# Function to check if the phone number is valid
def is_valid_phone_number(phone_number: str, country_code: str):
    try:
        parsed_number = parse(phone_number, country_code)  # Parse with country code
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
            if carrier_name:  # Only add numbers with valid carrier
                valid_numbers.append({"phone_number": phone_number, "carrier": carrier_name})
    return valid_numbers

# Endpoint to generate phone numbers
@app.post("/generate-numbers")
async def generate_numbers(country_code: str, prefix: str, amount: int):
    if not country_code.startswith("+"):
        raise HTTPException(status_code=400, detail="Country code must start with '+'")
    if not prefix.isdigit() or len(prefix) < 3:
        raise HTTPException(status_code=400, detail="Prefix must be a number with at least 3 digits")
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")

    valid_numbers = generate_phone_numbers(country_code, prefix, amount)
    return {"valid_numbers": valid_numbers}

# Endpoint to lookup a phone number
@app.get("/lookup-number")
async def lookup_number(phone_number: str, country_code: str):
    if not is_valid_phone_number(phone_number, country_code):
        raise HTTPException(status_code=400, detail="Invalid phone number")
    carrier_name = get_carrier(phone_number, country_code)
    if carrier_name:
        return {"carrier": carrier_name}
    return {"carrier": "Unknown"}

# Background task to save phone numbers to a CSV file
def save_to_csv(file_path: str, numbers: List[dict]):
    with open(file_path, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Phone Number", "Carrier"])
        for item in numbers:
            writer.writerow([item["phone_number"], item["carrier"]])

# Endpoint to generate phone numbers and download as CSV
@app.post("/generate-and-download")
async def generate_and_download(country_code: str, prefix: str, amount: int, background_tasks: BackgroundTasks):
    valid_numbers = generate_phone_numbers(country_code, prefix, amount)
    file_path = "generated_phone_numbers.csv"
    background_tasks.add_task(save_to_csv, file_path, valid_numbers)
    return {"detail": "CSV generation in progress", "file_path": file_path}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

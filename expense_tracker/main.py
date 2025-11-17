import json
from datetime import datetime

from numpy import exp

DATA_FILE = "data.json"

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)
    
def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)
        
def add_expense():
    amount = float(input("Enter amount:"))
    category = input("Enter category (Food, Travel, Shopping, etc.):")
    note = input("Add a note (optional):")
    
    expense = {
        "amount": amount,
        "category": category,
        "note": note,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    data = load_data()
    data["expenses"].append(expense)
    save_data(data)
    print("Expense added successfully!")
    
def view_expenses():
    data = load_data()
    expenses = data["expenses"]
    
    if not expenses:
        print("\nNo expenses recorded yet.\n")
        return
    
    print("\n---- All Expenses ----")
    for idx, expense in enumerate(expenses, 1):
        print(f"{idx}. ${exp['amount']} | {exp['category']} | {exp['date']} | {exp['note']}")
        print()

def monthly_summary():
        data = load_data()
        expenses = data["expenses"]
        
        total = sum(exp["amount"] for exp in expenses)
        print(f"\nTotal expenses: ${total}\n")
        
        
def main():
        while True:
            print("=== Expense Tracker ===")
            print("1. Add Expense")
            print("2. View All Expenses")
            print("3. Summary")
            print("4. Exit")
            
            choice = input("Choose Option: ")
            
            if choice == "1":
                add_expense()
            elif choice == "2":
                view_expenses()
            elif choice == "3":
                monthly_summary()
            elif choice == "4":
                print("Existing...")
                break
            else:
                print("Invalid choice.")
                
if __name__ == "__main__":
    main()

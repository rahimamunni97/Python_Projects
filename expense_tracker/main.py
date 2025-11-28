import json
from datetime import datetime
import csv

#from numpy import exp

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
        print(f"{idx}. ${expense['amount']} | {expense['category']} | {expense['date']} | {expense['note']}")
        print()

def monthly_summary():
        data = load_data()
        expenses = data["expenses"]
        
        total = sum(exp["amount"] for exp in expenses)
        print(f"\nTotal expenses: ${total}\n")
        
def summary_by_category():
    """Display total spending by category."""
    data = load_data()
    expenses = data["expenses"]
    
    if not expenses:
        print("\nNo expenses recorded yet. \n")
        return
    
    category_totals = {}
    for exp in expenses:
        category = exp["category"]
        category_totals[category] = category_totals.get(category, 0) + exp["amount"]
        
    print("\n---- Category Summary ----")
    for category, total in category_totals.items():
        print(f"{category}: ${total:.2f}")
        print()
        
def search_expenses():
    """Search expenses by category or note."""
    keyword = input("Enter category or keyword to search: ").lower()
    data = load_data()
    expenses = data["expenses"]      
    
    results = [exp for exp in expenses if keyword in exp["category"].lower() or keyword in exp["note"].lower()]
    
    if not results:
        print("\nNo matching expenses found.\n")
        return
    
    print("\n---- Search Results ----") 
    for idx, exp in enumerate(results, 1):
        print(f"{idx}.${exp['amount']:.2f} | {exp['category']} | {exp['date']} | {exp['note']}")
    print()

def delete_expense():
    """Delete an expense by number"""
    data = load_data()
    expenses = data["expenses"]
    
    if not expenses:
        print("\nNo expenses recorded yet.\n")
        return
    
    view_expenses()
    try:
        num = int(input("Enter expense number to delate: "))
        if 1 <= num <= len(expenses):
            removed = expenses.pop(num - 1)
            save_data(data)
            print(f"Deleted: {removed['category']} - ${removed['amount']:.2f}\n")
        else:
            print("Invalid number.\n")
    except ValueError:
        print("Please enter a valid number.\n")
        
def export_to_csv():
    """Export all expenses to a CSV file."""
    data = load_data()
    expenses = data["expenses"]
    
    if not expenses:
        print("\nNo expenses to export.\n")
        return
    
    with open("expenses.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Amount", "Category", "Note", "Date"])
        for exp in expenses:
            writer.writerow([exp["amount"], exp["category"], exp["note"], exp["date"]])
            
        print("Expenses exported to expenses.csv successfully!\n")
    
def main():
        while True:
            print("=== Expense Tracker ===")
            print("1. Add Expense")
            print("2. View All Expenses")
            print("3. Summary (Total)")
            print("4. Category Summary")
            print("5. Search Expenses")
            print("6. Delete Expense")
            print("7. Export to CSV")
            print("8. Exit")
            
            choice = input("Choose Option: ")
            
            if choice == "1":
                add_expense()
            elif choice == "2":
                view_expenses()
            elif choice == "3":
                monthly_summary()
            elif choice == "4":
                summary_by_category()
            elif choice == "5":
                search_expenses()
            elif choice == "6":
                delete_expense()
            elif choice == "7":
                export_to_csv()
            elif choice == "8":
                print("Existing...")
                break
            else:
                print("Invalid choice. Try again.")
                
if __name__ == "__main__":
    main()

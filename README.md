[README.md](https://github.com/user-attachments/files/35027463/README.md)
# CAMPUS-PHARMACY-PROJECT System 

TOOLS USED
Python 3 + tkinter + SQLite. Standard library only, so there is nothing to install.

## Files

| File | Purpose 
| `pharmacy.py` | Domain classes + SQLite + business rules |
| `app.py` | tkinter window |
| `test_pharmacy.py` | Automated tests |
|`pharmacy.db` | pharmacy database |
| `uml_diagram.png` | UML class diagram with key |

## 1. Create the database and load sample data

Nothing extra to do: the first time you run the app it creates `pharmacy.db`
with all tables (`CREATE TABLE IF NOT EXISTS`) and loads fictional sample data
(2 branches, 3 medicines, some stock). To start fresh, delete `pharmacy.db`.

## 2. Run the tkinter application

```
python app.py
```

## 3. Run the tests

```
python -m unittest test_pharmacy -v
```

## Sample data (all fictional)

- Branches: Main Campus, Satellite Clinic
- Medicines: PARA500, AMOX250, MORPH10 (controlled)
- Authorised prescribers: DR001, DR002, DR003
- Use any fictional patient ID, e.g. PAT-001

## Test checklist (do these by hand in the GUI)

1. Register a medicine with price `-5`  -> error "Price must be positive."
2. Register code `PARA500` again          -> error "already exists."
3. Prescription at Main Campus for `AMOX250` x 50 -> Dispense -> error "Not enough stock", status stays pending.
4. Prescription for `MORPH10` x 1 with prescriber `XYZ` -> Dispense -> error "not authorised".
5. Same prescription with prescriber `DR001` -> Dispense -> success.
6. Dispense that prescription again -> error "already been dispensed."
7. Open the "Low stock" tab -> AMOX250 (Main) and PARA500 (Satellite) are listed.
8. Close the app, reopen -> all data is still there.

## AI declaration

"Claude AI helped us debug the code; the group reviewed, and we did some research on tkinter because we had litte exposure to it, then tested and can explain every part.

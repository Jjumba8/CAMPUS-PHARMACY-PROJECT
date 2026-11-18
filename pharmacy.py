"""
pharmacy.py: the brain of the system (no tkinter in here).

Part 1: domain classes (Medicine, ControlledMedicine, Branch, PrescriptionLine, Prescription)
Part 2: Pharmacy class = talks to SQLite and applies the business rules.

Only the Python standard library is used (sqlite3).
"""
import sqlite3

# Simulated allow-list of prescribers (fictional codes only).
# A controlled medicine may only be dispensed if the prescriber code is in here.
ALLOWED_PRESCRIBERS = {"DR001", "DR002", "DR003"}

# The only three statuses a prescription may have.
VALID_STATUSES = ("pending", "dispensed", "cancelled")


# PART 1: DOMAIN CLASSES

class Medicine:
    """An ordinary medicine. Price and reorder level are protected by properties."""

    def __init__(self, code, name, price, reorder_level):
        # These assignments go through the property setters below,
        # so bad values are rejected the moment the object is created.
        self.code = code
        self.name = name
        self.price = price
        self.reorder_level = reorder_level

    # code: must not be empty
    @property
    def code(self):
        return self._code

    @code.setter
    def code(self, value):
        value = str(value).strip().upper()
        if value == "":
            raise ValueError("Medicine code cannot be empty.")
        self._code = value

    # name: must not be empty
    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        value = str(value).strip()
        if value == "":
            raise ValueError("Medicine name cannot be empty.")
        self._name = value

    # price: must be a number greater than 0
    @property
    def price(self):
        return self._price

    @price.setter
    def price(self, value):
        try:
            value = float(value)
        except (TypeError, ValueError):
            raise ValueError("Price must be a number.")
        if value <= 0:
            raise ValueError("Price must be positive.")
        self._price = value

    # reorder level: whole number, 0 or more
    @property
    def reorder_level(self):
        return self._reorder_level

    @reorder_level.setter
    def reorder_level(self, value):
        try:
            value = int(value)
        except (TypeError, ValueError):
            raise ValueError("Reorder level must be a whole number.")
        if value < 0:
            raise ValueError("Reorder level cannot be negative.")
        self._reorder_level = value

    def needs_authorisation(self):
        """Ordinary medicines do NOT need an authorised prescriber."""
        return False

    def describe(self):
        return f"{self.code} - {self.name} (ordinary)"


class ControlledMedicine(Medicine):
    """A controlled medicine. Inherits everything and OVERRIDES two methods."""

    def needs_authorisation(self):          # method overriding
        return True

    def describe(self):                     # method overriding
        return f"{self.code} - {self.name} (CONTROLLED)"


class Branch:
    """A dispensing point, e.g. 'Main Campus'."""

    def __init__(self, name):
        name = str(name).strip()
        if name == "":
            raise ValueError("Branch name cannot be empty.")
        self.name = name


class PrescriptionLine:
    """One line of a prescription: which medicine and how many."""

    def __init__(self, medicine_code, quantity):
        self.medicine_code = str(medicine_code).strip().upper()
        try:
            self.quantity = int(quantity)
        except (TypeError, ValueError):
            raise ValueError("Quantity must be a whole number.")
        if self.medicine_code == "":
            raise ValueError("Medicine code cannot be empty.")
        if self.quantity <= 0:
            raise ValueError("Quantity must be at least 1.")


class Prescription:
    """A prescription = patient + branch + prescriber + 1 or more lines + status."""

    def __init__(self, patient_id, branch, prescriber_code, lines, status="pending"):
        if str(patient_id).strip() == "":
            raise ValueError("Patient ID cannot be empty.")
        if len(lines) == 0:
            raise ValueError("A prescription needs at least one line.")
        self.patient_id = str(patient_id).strip()
        self.branch = branch
        self.prescriber_code = str(prescriber_code).strip().upper()
        self.lines = lines
        self.status = status  # goes through the property below

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        if value not in VALID_STATUSES:
            raise ValueError("Status must be pending, dispensed or cancelled.")
        self._status = value


def medicine_from_row(row):
    """Turn a database row into the right class (polymorphism in action)."""
    if row["controlled"] == 1:
        return ControlledMedicine(row["code"], row["name"], row["price"], row["reorder_level"])
    return Medicine(row["code"], row["name"], row["price"], row["reorder_level"])


# PART 2: DATABASE + RULES

class Pharmacy:
    """Saves everything in SQLite and enforces the business rules."""

    def __init__(self, db_file="pharmacy.db"):
        self.conn = sqlite3.connect(db_file)
        self.conn.row_factory = sqlite3.Row            # lets us use row["name"]
        self.conn.execute("PRAGMA foreign_keys = ON")  # SQLite ignores foreign keys unless told
        self._create_tables()

    def _create_tables(self):
        # CHECK constraints are a 2nd safety net: even if Python code slipped,
        # the database itself refuses negative stock / bad prices.
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS branches (
            name TEXT PRIMARY KEY
        );
        CREATE TABLE IF NOT EXISTS medicines (
            code          TEXT PRIMARY KEY,
            name          TEXT NOT NULL,
            price         REAL NOT NULL CHECK (price > 0),
            reorder_level INTEGER NOT NULL CHECK (reorder_level >= 0),
            controlled    INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS stock (
            branch   TEXT NOT NULL REFERENCES branches(name),
            code     TEXT NOT NULL REFERENCES medicines(code),
            quantity INTEGER NOT NULL CHECK (quantity >= 0),
            PRIMARY KEY (branch, code)
        );
        CREATE TABLE IF NOT EXISTS prescriptions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id      TEXT NOT NULL,
            branch          TEXT NOT NULL REFERENCES branches(name),
            prescriber_code TEXT,
            status          TEXT NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending','dispensed','cancelled'))
        );
        CREATE TABLE IF NOT EXISTS prescription_lines (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            prescription_id INTEGER NOT NULL REFERENCES prescriptions(id),
            code            TEXT NOT NULL REFERENCES medicines(code),
            quantity        INTEGER NOT NULL CHECK (quantity > 0)
        );
        """)
        self.conn.commit()

    # branches and medicines

    def add_branch(self, branch):
        try:
            with self.conn:
                self.conn.execute("INSERT INTO branches (name) VALUES (?)", (branch.name,))
        except sqlite3.IntegrityError:
            raise ValueError(f"Branch '{branch.name}' already exists.")

    def list_branches(self):
        rows = self.conn.execute("SELECT name FROM branches ORDER BY name").fetchall()
        return [r["name"] for r in rows]

    def add_medicine(self, medicine):
        # 'medicine' was already validated when the object was created.
        controlled = 1 if medicine.needs_authorisation() else 0   # polymorphism
        try:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO medicines (code, name, price, reorder_level, controlled) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (medicine.code, medicine.name, medicine.price,
                     medicine.reorder_level, controlled))
        except sqlite3.IntegrityError:
            raise ValueError(f"Medicine code '{medicine.code}' already exists.")

    def get_medicine(self, code):
        row = self.conn.execute("SELECT * FROM medicines WHERE code = ?",
                                (str(code).strip().upper(),)).fetchone()
        if row is None:
            raise ValueError(f"Medicine '{code}' does not exist.")
        return medicine_from_row(row)

    def list_medicines(self):
        rows = self.conn.execute("SELECT * FROM medicines ORDER BY code").fetchall()
        return [medicine_from_row(r) for r in rows]

    # stock

    def receive_stock(self, branch_name, code, quantity):
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            raise ValueError("Quantity must be a whole number.")
        if quantity <= 0:
            raise ValueError("Quantity received must be at least 1.")
        if branch_name not in self.list_branches():
            raise ValueError(f"Branch '{branch_name}' does not exist.")
        medicine = self.get_medicine(code)       # raises if the medicine is unknown
        with self.conn:
            # Insert a new stock row, or add to the existing one.
            self.conn.execute(
                "INSERT INTO stock (branch, code, quantity) VALUES (?, ?, ?) "
                "ON CONFLICT(branch, code) DO UPDATE SET quantity = quantity + excluded.quantity",
                (branch_name, medicine.code, quantity))

    def get_quantity(self, branch_name, code):
        row = self.conn.execute("SELECT quantity FROM stock WHERE branch=? AND code=?",
                                (branch_name, str(code).strip().upper())).fetchone()
        return row["quantity"] if row else 0

    def low_stock(self):
        """Rows where quantity <= reorder level, per branch."""
        rows = self.conn.execute("""
            SELECT s.branch, m.code, m.name, s.quantity, m.reorder_level
            FROM stock s JOIN medicines m ON m.code = s.code
            WHERE s.quantity <= m.reorder_level
            ORDER BY s.branch, m.code
        """).fetchall()
        return [tuple(r) for r in rows]

    # prescriptions

    def create_prescription(self, rx):
        if rx.branch not in self.list_branches():
            raise ValueError(f"Branch '{rx.branch}' does not exist.")
        for line in rx.lines:
            self.get_medicine(line.medicine_code)   # every medicine must exist
        with self.conn:   # all inserts succeed together or not at all
            cur = self.conn.execute(
                "INSERT INTO prescriptions (patient_id, branch, prescriber_code, status) "
                "VALUES (?, ?, ?, 'pending')",
                (rx.patient_id, rx.branch, rx.prescriber_code))
            rx_id = cur.lastrowid
            for line in rx.lines:
                self.conn.execute(
                    "INSERT INTO prescription_lines (prescription_id, code, quantity) "
                    "VALUES (?, ?, ?)", (rx_id, line.medicine_code, line.quantity))
        return rx_id

    def list_prescriptions(self):
        rows = self.conn.execute(
            "SELECT id, patient_id, branch, prescriber_code, status "
            "FROM prescriptions ORDER BY id").fetchall()
        return [tuple(r) for r in rows]

    def dispense(self, rx_id):
        """
        Atomic dispensing.
        Everything between BEGIN and COMMIT is ONE unit. If any rule fails we raise
        an error, ROLLBACK undoes every change, and the prescription stays pending.
        """
        rx = self.conn.execute("SELECT * FROM prescriptions WHERE id = ?", (rx_id,)).fetchone()
        if rx is None:
            raise ValueError(f"Prescription {rx_id} does not exist.")

        self.conn.execute("BEGIN")
        try:
            # Rule: only 'pending' prescriptions can be dispensed.
            if rx["status"] == "dispensed":
                raise ValueError("This prescription has already been dispensed.")
            if rx["status"] == "cancelled":
                raise ValueError("A cancelled prescription cannot be dispensed.")

            lines = self.conn.execute(
                "SELECT code, quantity FROM prescription_lines WHERE prescription_id = ?",
                (rx_id,)).fetchall()

            for line in lines:
                medicine = self.get_medicine(line["code"])

                # Rule: controlled medicine needs a prescriber on the allow-list.
                # We do NOT care which class it is: we just ask the object (polymorphism).
                if medicine.needs_authorisation():
                    if rx["prescriber_code"] not in ALLOWED_PRESCRIBERS:
                        raise ValueError(
                            f"{medicine.name} is controlled: prescriber "
                            f"'{rx['prescriber_code']}' is not authorised.")

                # Rule: no overselling. The WHERE quantity >= ? means the row is only
                # changed when there is enough stock; rowcount 0 means 'not enough'.
                cur = self.conn.execute(
                    "UPDATE stock SET quantity = quantity - ? "
                    "WHERE branch = ? AND code = ? AND quantity >= ?",
                    (line["quantity"], rx["branch"], line["code"], line["quantity"]))
                if cur.rowcount == 0:
                    raise ValueError(
                        f"Not enough stock of {medicine.name} at {rx['branch']}.")

            # All lines worked, so now mark the prescription as dispensed.
            self.conn.execute("UPDATE prescriptions SET status = 'dispensed' WHERE id = ?",
                              (rx_id,))
            self.conn.commit()          # make everything permanent together
        except Exception:
            self.conn.rollback()        # undo every stock change made so far
            raise                       # pass the error on so the GUI can show it

    def cancel_prescription(self, rx_id):
        row = self.conn.execute("SELECT status FROM prescriptions WHERE id = ?",
                                (rx_id,)).fetchone()
        if row is None:
            raise ValueError(f"Prescription {rx_id} does not exist.")
        if row["status"] != "pending":
            raise ValueError("Only a pending prescription can be cancelled.")
        with self.conn:
            self.conn.execute("UPDATE prescriptions SET status = 'cancelled' WHERE id = ?",
                              (rx_id,))

    # sample data (fictional only)

    def seed_sample_data(self):
        """Fill an empty database with fictional demo data."""
        if self.list_medicines():
            return  # already has data, do nothing
        self.add_branch(Branch("Main Campus"))
        self.add_branch(Branch("Satellite Clinic"))
        self.add_medicine(Medicine("PARA500", "Paracetamol 500mg", 500, 20))
        self.add_medicine(Medicine("AMOX250", "Amoxicillin 250mg", 1500, 10))
        self.add_medicine(ControlledMedicine("MORPH10", "Morphine 10mg", 8000, 5))
        self.receive_stock("Main Campus", "PARA500", 100)
        self.receive_stock("Main Campus", "AMOX250", 8)      # already low stock
        self.receive_stock("Main Campus", "MORPH10", 20)
        self.receive_stock("Satellite Clinic", "PARA500", 15)  # low stock here

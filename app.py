"""
app.py: the tkinter window. It only shows things and passes button clicks to
the Pharmacy class. No business rules live here.
Run with:  python app.py
"""
import tkinter as tk
from tkinter import ttk, messagebox

from pharmacy import (Pharmacy, Medicine, ControlledMedicine, Branch,
                      Prescription, PrescriptionLine)


class App(tk.Tk):
    def __init__(self, pharmacy):
        super().__init__()
        self.title("UCU Campus Pharmacy")
        self.geometry("760x520")
        self.pharmacy = pharmacy
        self.rx_lines = []          # lines of the prescription being built (not saved yet)

        # One tab per job.
        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True, padx=8, pady=8)
        self.tab_med = ttk.Frame(tabs)
        self.tab_stock = ttk.Frame(tabs)
        self.tab_rx = ttk.Frame(tabs)
        self.tab_low = ttk.Frame(tabs)
        tabs.add(self.tab_med, text="Register medicine")
        tabs.add(self.tab_stock, text="Branches & stock")
        tabs.add(self.tab_rx, text="Prescriptions")
        tabs.add(self.tab_low, text="Low stock")

        self.build_medicine_tab()
        self.build_stock_tab()
        self.build_prescription_tab()
        self.build_low_stock_tab()
        self.refresh_all()

    # small helpers

    def add_field(self, parent, label, row):
        """Put a label and an entry box on one row; return the entry."""
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=5, pady=3)
        entry = ttk.Entry(parent, width=25)
        entry.grid(row=row, column=1, padx=5, pady=3)
        return entry

    def run(self, action):
        """Run an action; if the pharmacy raises ValueError, show it in a popup."""
        try:
            action()
            return True
        except ValueError as error:
            messagebox.showerror("Not allowed", str(error))
            return False

    # tab 1: register medicine

    def build_medicine_tab(self):
        f = self.tab_med
        self.m_code = self.add_field(f, "Code", 0)
        self.m_name = self.add_field(f, "Name", 1)
        self.m_price = self.add_field(f, "Unit price (UGX)", 2)
        self.m_reorder = self.add_field(f, "Reorder level", 3)
        self.m_controlled = tk.BooleanVar()
        ttk.Checkbutton(f, text="Controlled medicine",
                        variable=self.m_controlled).grid(row=4, column=1, sticky="w")
        ttk.Button(f, text="Save medicine", command=self.save_medicine).grid(row=5, column=1, pady=8)

        self.med_table = ttk.Treeview(f, columns=("code", "name", "price", "reorder", "type"),
                                      show="headings", height=10)
        for col, title in zip(self.med_table["columns"],
                              ["Code", "Name", "Price", "Reorder", "Type"]):
            self.med_table.heading(col, text=title)
            self.med_table.column(col, width=110)
        self.med_table.grid(row=6, column=0, columnspan=3, padx=5, pady=5)

    def save_medicine(self):
        def action():
            # Choose the class from the tick box; the class itself checks price etc.
            kind = ControlledMedicine if self.m_controlled.get() else Medicine
            medicine = kind(self.m_code.get(), self.m_name.get(),
                            self.m_price.get(), self.m_reorder.get())
            self.pharmacy.add_medicine(medicine)
        if self.run(action):
            messagebox.showinfo("Saved", "Medicine registered.")
            self.refresh_all()

    # tab 2: branches and stock

    def build_stock_tab(self):
        f = self.tab_stock
        self.b_name = self.add_field(f, "New branch name", 0)
        ttk.Button(f, text="Add branch", command=self.save_branch).grid(row=0, column=2)

        ttk.Label(f, text="Branch").grid(row=1, column=0, sticky="w", padx=5, pady=10)
        self.s_branch = ttk.Combobox(f, state="readonly", width=22)
        self.s_branch.grid(row=1, column=1)
        self.s_code = self.add_field(f, "Medicine code", 2)
        self.s_qty = self.add_field(f, "Quantity received", 3)
        ttk.Button(f, text="Receive stock", command=self.receive_stock).grid(row=4, column=1, pady=8)

        self.stock_label = ttk.Label(f, text="")
        self.stock_label.grid(row=5, column=0, columnspan=3)

    def save_branch(self):
        if self.run(lambda: self.pharmacy.add_branch(Branch(self.b_name.get()))):
            self.refresh_all()

    def receive_stock(self):
        def action():
            self.pharmacy.receive_stock(self.s_branch.get(), self.s_code.get(), self.s_qty.get())
        if self.run(action):
            now = self.pharmacy.get_quantity(self.s_branch.get(), self.s_code.get())
            self.stock_label.config(text=f"Stock of {self.s_code.get().upper()} "
                                         f"at {self.s_branch.get()} is now {now}")
            self.refresh_all()

    # tab 3: prescriptions

    def build_prescription_tab(self):
        f = self.tab_rx
        self.r_patient = self.add_field(f, "Patient ID (fictional)", 0)
        ttk.Label(f, text="Branch").grid(row=1, column=0, sticky="w", padx=5)
        self.r_branch = ttk.Combobox(f, state="readonly", width=22)
        self.r_branch.grid(row=1, column=1)
        self.r_prescriber = self.add_field(f, "Prescriber code", 2)
        self.r_code = self.add_field(f, "Medicine code", 3)
        self.r_qty = self.add_field(f, "Quantity", 4)
        ttk.Button(f, text="Add line", command=self.add_line).grid(row=3, column=2)
        ttk.Button(f, text="Save prescription", command=self.save_prescription).grid(row=4, column=2)

        self.lines_box = tk.Listbox(f, height=3, width=30)
        self.lines_box.grid(row=5, column=1, pady=4)

        self.rx_table = ttk.Treeview(f, columns=("id", "patient", "branch", "prescriber", "status"),
                                     show="headings", height=7)
        for col, title in zip(self.rx_table["columns"],
                              ["ID", "Patient", "Branch", "Prescriber", "Status"]):
            self.rx_table.heading(col, text=title)
            self.rx_table.column(col, width=110)
        self.rx_table.grid(row=6, column=0, columnspan=3, padx=5, pady=5)

        ttk.Button(f, text="Dispense selected", command=self.dispense).grid(row=7, column=0)
        ttk.Button(f, text="Cancel selected", command=self.cancel).grid(row=7, column=1)

    def add_line(self):
        def action():
            line = PrescriptionLine(self.r_code.get(), self.r_qty.get())  # validates
            self.rx_lines.append(line)
            self.lines_box.insert("end", f"{line.medicine_code} x {line.quantity}")
        self.run(action)

    def save_prescription(self):
        def action():
            rx = Prescription(self.r_patient.get(), self.r_branch.get(),
                              self.r_prescriber.get(), self.rx_lines)
            self.pharmacy.create_prescription(rx)
        if self.run(action):
            self.rx_lines = []              # start a fresh prescription
            self.lines_box.delete(0, "end")
            self.refresh_all()

    def selected_rx_id(self):
        chosen = self.rx_table.selection()
        if not chosen:
            messagebox.showwarning("Select one", "Click a prescription in the table first.")
            return None
        return int(self.rx_table.item(chosen[0])["values"][0])

    def dispense(self):
        rx_id = self.selected_rx_id()
        if rx_id is not None:
            if self.run(lambda: self.pharmacy.dispense(rx_id)):
                messagebox.showinfo("Done", f"Prescription {rx_id} dispensed.")
            self.refresh_all()      # refresh even on failure (shows it is still pending)

    def cancel(self):
        rx_id = self.selected_rx_id()
        if rx_id is not None:
            self.run(lambda: self.pharmacy.cancel_prescription(rx_id))
            self.refresh_all()

    # tab 4: low stock

    def build_low_stock_tab(self):
        f = self.tab_low
        self.low_table = ttk.Treeview(f, columns=("branch", "code", "name", "qty", "reorder"),
                                      show="headings", height=15)
        for col, title in zip(self.low_table["columns"],
                              ["Branch", "Code", "Medicine", "Quantity", "Reorder level"]):
            self.low_table.heading(col, text=title)
            self.low_table.column(col, width=130)
        self.low_table.pack(padx=5, pady=5)
        ttk.Button(f, text="Refresh", command=self.refresh_all).pack()

    # reload every table from the database

    def fill(self, table, rows):
        table.delete(*table.get_children())
        for row in rows:
            table.insert("", "end", values=row)

    def refresh_all(self):
        branches = self.pharmacy.list_branches()
        self.s_branch["values"] = branches
        self.r_branch["values"] = branches
        self.fill(self.med_table, [(m.code, m.name, m.price, m.reorder_level,
                                    "Controlled" if m.needs_authorisation() else "Ordinary")
                                   for m in self.pharmacy.list_medicines()])
        self.fill(self.rx_table, self.pharmacy.list_prescriptions())
        self.fill(self.low_table, self.pharmacy.low_stock())


if __name__ == "__main__":
    pharmacy = Pharmacy("pharmacy.db")
    pharmacy.seed_sample_data()      # only fills the database if it is empty
    App(pharmacy).mainloop()

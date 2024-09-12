import heapq
from collections import deque, defaultdict
from datetime import datetime, date
import io
from matplotlib import pyplot as plt
from sqlalchemy.exc import IntegrityError
from flask import Flask, request, jsonify, render_template, redirect, send_file, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import heapq
from collections import deque, defaultdict
import networkx as nx

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key_here'  # Required for flash messages
db = SQLAlchemy(app)

# Database Models
class Patient(db.Model):
    id = db.Column(db.String(10), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)

class Appointment(db.Model):
    id = db.Column(db.String(10), primary_key=True)
    patient_id = db.Column(db.String(10), db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.String(10), db.ForeignKey('staff.id'), nullable=False)
    time = db.Column(db.DateTime, nullable=False)

class Staff(db.Model):
    id = db.Column(db.String(10), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False)

class InventoryItem(db.Model):
    id = db.Column(db.String(10), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

class BillingRecord(db.Model):
    id = db.Column(db.String(10), primary_key=True)
    patient_id = db.Column(db.String(10), db.ForeignKey('patient.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

# Hospital Management System
class HospitalManagementSystem:
    def __init__(self):
        self.graph = defaultdict(list)
        self.locations = set()
        self.appointment_heap = []
        self.staff_list = []  # Add this line
        self.inventory_queue = deque()
        self.graph = nx.Graph()
        self.appointment_heap = []
        self.billing_bst = None

    def add_patient(self, patient):
        db.session.add(patient)
        db.session.commit()
        self.add_notification(f"New patient added: {patient.name}")
        return True

    def get_patient(self, patient_id):
        return Patient.query.get(patient_id)

    def update_patient(self, patient_id, updated_info):
        patient = Patient.query.get(patient_id)
        if patient:
            for key, value in updated_info.items():
                setattr(patient, key, value)
            db.session.commit()
            self.add_notification(f"Patient information updated: {patient.name}")
            return True
        return False

    def delete_patient(self, patient_id):
        patient = Patient.query.get(patient_id)
        if patient:
            db.session.delete(patient)
            db.session.commit()
            self.add_notification(f"Patient deleted: {patient.name}")
            return True
        return False

    def schedule_appointment(self, appointment):
        db.session.add(appointment)
        db.session.commit()
        heapq.heappush(self.appointment_heap, (appointment.time, appointment.id))
        self.add_notification(f"New appointment scheduled for patient ID: {appointment.patient_id}")
        return True

    def get_next_appointment(self):
        while self.appointment_heap:
            time, appointment_id = heapq.heappop(self.appointment_heap)
            appointment = Appointment.query.get(appointment_id)
            if appointment:
                return appointment
        return None

    def cancel_appointment(self, appointment_id):
        appointment = Appointment.query.get(appointment_id)
        if appointment:
            db.session.delete(appointment)
            db.session.commit()
            self.appointment_heap = [(time, id) for time, id in self.appointment_heap if id != appointment_id]
            heapq.heapify(self.appointment_heap)
            self.add_notification(f"Appointment cancelled for patient ID: {appointment.patient_id}")
            return True
        return False

    def reschedule_appointment(self, appointment_id, new_time):
        appointment = Appointment.query.get(appointment_id)
        if appointment:
            self.cancel_appointment(appointment_id)
            appointment.time = new_time
            return self.schedule_appointment(appointment)
        return False

    def get_appointments(self):
        return Appointment.query.order_by(Appointment.time).all()

    # Update this method
    def add_staff(self, staff):
        db.session.add(staff)
        db.session.commit()
        self.staff_list.append(staff)
        self.add_notification(f"New staff member added: {staff.name}")
        return True
    def remove_staff(self, staff_id):
        staff = Staff.query.get(staff_id)
        if staff:
            db.session.delete(staff)
            db.session.commit()
            self.staff_list = [s for s in self.staff_list if s.id != staff_id]
            self.add_notification(f"Staff member removed: {staff.name}")
            return True
        return False

    def update_staff(self, staff_id, updated_info):
        staff = Staff.query.get(staff_id)
        if staff:
            for key, value in updated_info.items():
                setattr(staff, key, value)
            db.session.commit()
            self.add_notification(f"Staff information updated: {staff.name}")
            return True
        return False

    def get_staff(self):
        if not self.staff_list:
            self.staff_list = Staff.query.all()
        return self.staff_list


    # Medical Inventory Management
    def add_inventory(self, item_data):
        item = InventoryItem(**item_data)
        db.session.add(item)
        db.session.commit()
        self.inventory_queue.append(item)
        self.add_notification(f"New inventory item added: {item.name}")
        return item.id  # Return the ID of the newly added item

    def get_inventory(self):
        if not self.inventory_queue:
            self.inventory_queue = deque(InventoryItem.query.all())
        return list(self.inventory_queue)

    def remove_inventory(self):
        if self.inventory_queue:
            item = self.inventory_queue.popleft()
            db.session.delete(item)
            db.session.commit()
            self.add_notification(f"Inventory item used: {item.name}")
            return item
        return None


    # Billing and Financial Records
    class BSTNode:
        def __init__(self, record):
            self.record = record
            self.left = None
            self.right = None
            
    def get_billing_records(self, patient_id):
        return BillingRecord.query.filter_by(patient_id=patient_id).all()


    def insert_billing_record(self, record):
        db.session.add(record)
        db.session.commit()
        self.billing_bst = self._insert_bst(self.billing_bst, record)
        self.add_notification(f"New billing record added for patient ID: {record.patient_id}")
        return True

    def _insert_bst(self, node, record):
        if not node:
            return self.BSTNode(record)
        if record.patient_id < node.record.patient_id:
            node.left = self._insert_bst(node.left, record)
        else:
            node.right = self._insert_bst(node.right, record)
        return node

    def search_billing_records(self, patient_id):
        return self.get_billing_records(patient_id)

    def _search_bst(self, node, patient_id):
        if not node or node.record.patient_id == patient_id:
            return [node.record] if node else []
        if patient_id < node.record.patient_id:
            return self._search_bst(node.left, patient_id)
        return self._search_bst(node.right, patient_id)

    def update_billing_record(self, record_id, updated_info):
        record = BillingRecord.query.get(record_id)
        if record:
            for key, value in updated_info.items():
                setattr(record, key, value)
            db.session.commit()
            self.billing_bst = self._rebuild_bst()
            self.add_notification(f"Billing record updated for patient ID: {record.patient_id}")
            return True
        return False

    def delete_billing_record(self, record_id):
        record = BillingRecord.query.get(record_id)
        if record:
            db.session.delete(record)
            db.session.commit()
            self.billing_bst = self._rebuild_bst()
            self.add_notification(f"Billing record deleted for patient ID: {record.patient_id}")
            return True
        return False

    def _rebuild_bst(self):
        records = BillingRecord.query.order_by(BillingRecord.patient_id).all()
        return self._build_balanced_bst(records, 0, len(records) - 1)

    def _build_balanced_bst(self, records, start, end):
        if start > end:
            return None
        mid = (start + end) // 2
        node = self.BSTNode(records[mid])
        node.left = self._build_balanced_bst(records, start, mid - 1)
        node.right = self._build_balanced_bst(records, mid + 1, end)
        return node

    def generate_financial_report(self, start_date, end_date):
        records = BillingRecord.query.filter(BillingRecord.date.between(start_date, end_date)).all()
        total_amount = sum(record.amount for record in records)
        return {
            'total_amount': total_amount,
            'record_count': len(records),
            'start_date': start_date,
            'end_date': end_date
        }

    def add_notification(self, message):
        notification = Notification(message=message)
        db.session.add(notification)
        db.session.commit()

    def get_notifications(self):
        return Notification.query.order_by(Notification.timestamp.desc()).limit(5).all()
    
    def sort_patients_by_name(self):
        patients = Patient.query.all()
        return sorted(patients, key=lambda x: x.name)

    def binary_search_patient_by_name(self, name):
        patients = self.sort_patients_by_name()
        left, right = 0, len(patients) - 1
        while left <= right:
            mid = (left + right) // 2
            if patients[mid].name == name:
                return patients[mid]
            elif patients[mid].name < name:
                left = mid + 1
            else:
                right = mid - 1
        return None

    def add_hospital_location(self, location):
        self.graph.add_node(location)
        return True

    def add_path(self, start, end):
        if start in self.graph.nodes and end in self.graph.nodes:
            self.graph.add_edge(start, end)
            return True
        return False

    def find_path(self, start, end):
        try:
            path = nx.shortest_path(self.graph, start, end)
            return path
        except nx.NetworkXNoPath:
            return None

# Initialize the Hospital Management System
hms = HospitalManagementSystem()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/patients')
def patients():
    all_patients = Patient.query.all()
    return render_template('patients.html', patients=all_patients)

@app.route('/patient/add', methods=['GET', 'POST'])
def add_patient():
    if request.method == 'POST':
        patient_id = request.form['patient_id']
        name = request.form['name']
        age = int(request.form['age'])
        gender = request.form['gender']

        existing_patient = Patient.query.get(patient_id)
        if existing_patient:
            flash(f'A patient with ID {patient_id} already exists.', 'error')
            return render_template('add_patient.html', 
                                   prefill={'name': name, 'age': age, 'gender': gender})

        new_patient = Patient(id=patient_id, name=name, age=age, gender=gender)
        
        try:
            hms.add_patient(new_patient)
            flash('Patient added successfully!', 'success')
            return redirect(url_for('patients'))
        except IntegrityError:
            db.session.rollback()
            flash(f'An error occurred. Patient with ID {patient_id} might already exist.', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'error')
    
    return render_template('add_patient.html')

@app.route('/patients/sorted')
def sorted_patients():
    sorted_patients = hms.sort_patients_by_name()
    return render_template('sorted_patients.html', patients=sorted_patients)

@app.route('/patients/search', methods=['GET', 'POST'])
def search_patient():
    if request.method == 'POST':
        name = request.form['name']
        patient = hms.binary_search_patient_by_name(name)
        if patient:
            return render_template('patient_details.html', patient=patient)
        else:
            flash('Patient not found', 'error')
    return render_template('search_patient.html')

@app.route('/appointments')
def appointments():
    all_appointments = hms.get_appointments()
    return render_template('appointments.html', appointments=all_appointments)

@app.route('/appointment/schedule', methods=['GET', 'POST'])
def schedule_appointment():
    if request.method == 'POST':
        appointment = Appointment(
            id=request.form['appointment_id'],
            patient_id=request.form['patient_id'],
            doctor_id=request.form['doctor_id'],
            time=datetime.strptime(request.form['time'], '%Y-%m-%dT%H:%M')
        )
        success = hms.schedule_appointment(appointment)
        if success:
            flash('Appointment scheduled successfully!', 'success')
            return redirect(url_for('appointments'))
        else:
            flash('Failed to schedule appointment.', 'error')
    return render_template('schedule_appointment.html')

@app.route('/appointment/cancel/<appointment_id>', methods=['POST'])
def cancel_appointment(appointment_id):
    success = hms.cancel_appointment(appointment_id)
    if success:
        flash('Appointment cancelled successfully!', 'success')
    else:
        flash('Failed to cancel appointment.', 'error')
    return redirect(url_for('appointments'))

@app.route('/appointment/reschedule/<appointment_id>', methods=['POST'])
def reschedule_appointment(appointment_id):
    new_time = datetime.strptime(request.form['new_time'], '%Y-%m-%dT%H:%M')
    success = hms.reschedule_appointment(appointment_id, new_time)
    if success:
        flash('Appointment rescheduled successfully!', 'success')
    else:
        flash('Failed to reschedule appointment.', 'error')
    return redirect(url_for('appointments'))


@app.route('/staff')
def staff():
    all_staff = hms.get_staff()
    return render_template('staff.html', staff=all_staff)

@app.route('/staff/add', methods=['GET', 'POST'])
def add_staff():
    if request.method == 'POST':
        staff = Staff(
            id=request.form['staff_id'],
            name=request.form['name'],
            role=request.form['role']
        )
        success = hms.add_staff(staff)
        if success:
            flash('Staff member added successfully!', 'success')
            return redirect(url_for('staff'))
        else:
            flash('Failed to add staff member.', 'error')
    return render_template('add_staff.html')

@app.route('/staff/remove/<staff_id>', methods=['POST'])
def remove_staff(staff_id):
    success = hms.remove_staff(staff_id)
    if success:
        flash('Staff member removed successfully!', 'success')
    else:
        flash('Failed to remove staff member.', 'error')
    return redirect(url_for('staff'))

@app.route('/staff/update/<staff_id>', methods=['POST'])
def update_staff(staff_id):
    updated_info = {
        'name': request.form['name'],
        'role': request.form['role']
    }
    success = hms.update_staff(staff_id, updated_info)
    if success:
        flash('Staff information updated successfully!', 'success')
    else:
        flash('Failed to update staff information.', 'error')
    return redirect(url_for('staff'))

@app.route('/inventory/add', methods=['GET', 'POST'])
def add_inventory():
    if request.method == 'POST':
        item_data = {
            'id': request.form['item_id'],
            'name': request.form['name'],
            'quantity': int(request.form['quantity'])
        }
        try:
            item_id = hms.add_inventory(item_data)
            flash('Inventory item added successfully!', 'success')
            return redirect(url_for('inventory'))
        except IntegrityError:
            db.session.rollback()
            flash('An error occurred. Item ID might already exist.', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'error')
    return render_template('add_inventory.html')

@app.route('/inventory')
def inventory():
    all_items = InventoryItem.query.all()  # Query directly from the database
    return render_template('inventory.html', items=all_items)

@app.route('/inventory/update', methods=['POST'])
def update_inventory():
    item_id = request.form['item_id']
    quantity_change = int(request.form['quantity_change'])
    success = hms.update_inventory(item_id, quantity_change)
    if success:
        flash('Inventory updated successfully!', 'success')
    else:
        flash('Failed to update inventory.', 'error')
    return redirect(url_for('inventory'))

@app.route('/inventory/remove', methods=['POST'])
def remove_inventory():
    item = hms.remove_inventory()
    if item:
        flash(f'Inventory item used: {item.name}', 'success')
    else:
        flash('No inventory items available.', 'error')
    return redirect(url_for('inventory'))

@app.route('/billing/<patient_id>')
def billing(patient_id):
    records = hms.get_billing_records(patient_id)
    return render_template('billing.html', records=records, patient_id=patient_id)


@app.route('/billing/add', methods=['GET', 'POST'])
def add_billing():
    if request.method == 'POST':
        record = BillingRecord(
            id=request.form['record_id'],
            patient_id=request.form['patient_id'],
            amount=float(request.form['amount']),
            date=datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        )
        success = hms.add_billing_record(record)
        if success:
            flash('Billing record added successfully!', 'success')
            return redirect(url_for('billing', patient_id=record.patient_id))
        else:
            flash('Failed to add billing record.', 'error')
    return render_template('add_billing.html')

@app.route('/billing/search', methods=['POST'])
def search_billing_records():
    patient_id = request.form['patient_id']
    records = hms.search_billing_records(patient_id)
    return render_template('billing.html', records=records, patient_id=patient_id)

@app.route('/billing/update/<record_id>', methods=['POST'])
def update_billing_record(record_id):
    updated_info = {
        'amount': float(request.form['amount']),
        'date': datetime.strptime(request.form['date'], '%Y-%m-%d').date()
    }
    success = hms.update_billing_record(record_id, updated_info)
    if success:
        flash('Billing record updated successfully!', 'success')
    else:
        flash('Failed to update billing record.', 'error')
    return redirect(url_for('billing', patient_id=request.form['patient_id']))

@app.route('/billing/delete/<record_id>', methods=['POST'])
def delete_billing_record(record_id):
    success = hms.delete_billing_record(record_id)
    if success:
        flash('Billing record deleted successfully!', 'success')
    else:
        flash('Failed to delete billing record.', 'error')
    return redirect(url_for('billing', patient_id=request.form['patient_id']))

@app.route('/billing/report', methods=['GET', 'POST'])
def financial_report():
    if request.method == 'POST':
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
        report = hms.generate_financial_report(start_date, end_date)
        return render_template('financial_report.html', report=report)
    return render_template('financial_report_form.html')


@app.route('/notifications')
def get_notifications():
    notifications = hms.get_notifications()
    return jsonify([{'message': n.message, 'timestamp': n.timestamp.isoformat()} for n in notifications])

@app.route('/navigation')
def navigation():
    return render_template('navigation.html')

@app.route('/navigation/add_location', methods=['POST'])
def add_location():
    location = request.form['location']
    success = hms.add_hospital_location(location)
    if success:
        flash('Location added successfully!', 'success')
    else:
        flash('Failed to add location. It might already exist.', 'error')
    return redirect(url_for('navigation'))

@app.route('/navigation/add_path', methods=['POST'])
def add_path():
    start = request.form['start']
    end = request.form['end']
    success = hms.add_path(start, end)
    if success:
        flash('Path added successfully!', 'success')
    else:
        flash('Failed to add path. Make sure both locations exist.', 'error')
    return redirect(url_for('navigation'))

@app.route('/navigation/visualize')
def visualize_hospital_layout():
    plt.figure(figsize=(12, 8))
    pos = nx.spring_layout(hms.graph)
    nx.draw(hms.graph, pos, with_labels=True, node_color='lightblue', node_size=500, font_size=10, font_weight='bold')
    edge_labels = nx.get_edge_attributes(hms.graph, 'weight')
    nx.draw_networkx_edge_labels(hms.graph, pos, edge_labels=edge_labels)
    
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    
    return send_file(img, mimetype='image/png')


@app.route('/navigation/find_path', methods=['POST'])
def find_path():
    start = request.form['start']
    end = request.form['end']
    path = hms.find_path(start, end)
    if path:
        return jsonify({'path': path})
    else:
        return jsonify({'error': 'No path found'}), 404

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
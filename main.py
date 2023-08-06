import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import json
from flask_jwt_extended import JWTManager, create_access_token, get_jwt_identity, jwt_required

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance_app.db'  
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 3600
db = SQLAlchemy(app)
jwt = JWTManager(app)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    balance = db.Column(db.Float, default=0.0, nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'
user1 = User(username='Sarvesh', balance=100.0)
user2 = User(username='Ram', balance=50.0)
user3 = User(username='John', balance=75.0)

db.session.add(user1)
db.session.add(user2)
db.session.add(user3)
db.session.commit()
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(200), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
class Split(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)

class GroupMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) 
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    split_id = db.Column(db.Integer, db.ForeignKey('split.id'), nullable=False)
@app.route('/signup', methods=['POST'])
def signup():
    data = json.loads(request.data)
    username = data.get('username')
    password = data.get('password')
    

    if not username or not password:
        return jsonify({'message': 'Missing username or balance'}), 400

    user = User.query.filter_by(username=username).first()
    if user:
        return jsonify({'message': 'Username already exists'}), 409

    new_user = User(username=username, password=password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User created successfully'}), 201


@app.route('/login', methods=['POST'])
def login():
    data = json.loads(request.data)
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username, password=password).first()
    if not user:
        return jsonify({'message': 'Invalid credentials'}), 401
    access_token = create_access_token(identity=user.id)
    return jsonify({'access_token': access_token}), 200

@app.route('/user/<int:user_id>', methods=['GET'])
def get_user_details(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404

    return jsonify({'user_details': {
        'id': user.id,
        'username': user.username,
        'balance' : user.balance
        
    }}), 200
@app.route('/home', methods=['GET'])
def home():
   
    user_id = get_jwt_identity()
    user = User.query.filter_by(id=user_id).first()

    if user:
       
        return jsonify({'username': user.username, 'balance': user.balance}), 200
    else:
        return jsonify({'message': 'User not found'}), 404\
        @app.route('/users', methods=['GET'])
def list_users():
    
    users = User.query.all()

    
    user_list = [user.username for user in users]
    return jsonify({'users': user_list}), 200
class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    payer_id = db.Column(db.Integer, nullable=False)
    payee_id = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f'<Payment {self.amount} from {self.payer_id} to {self.payee_id}>'

@app.route('/settle_payment', methods=['POST'])
def settle_payment():

    data = request.json
    payer_id = data.get('payer_id')
    payee_id = data.get('payee_id')
    amount = data.get('amount')
    payer = User.query.get(payer_id)
    payee = User.query.get(payee_id)
    if not payer or not payee:
        return jsonify({'error': 'Invalid payer or payee ID'}), 400

   
    if payer.balance < amount:
        return jsonify({'error': 'Insufficient balance for payment settlement'}), 400

   
    payer.balance -= amount
    payee.balance += amount
    db.session.commit()

    
    payment = Payment(payer_id=payer_id, payee_id=payee_id, amount=amount)
    db.session.add(payment)
    db.session.commit()

    return jsonify({'message': 'Payment settled successfully'}), 200
@app.route('/create_split', methods=['POST'])
def create_split():
    
    data = request.json
    selected_user_ids = data.get('selected_users')  
    total_amount = data.get('total_amount') 

    
    users = User.query.filter(User.id.in_(selected_user_ids)).all()
    if len(users) != len(selected_user_ids):
        return jsonify({'error': 'Invalid user ID(s) in the split'}), 400

    
    num_users = len(users)
    split_amount_per_user = total_amount / num_users

    
    for user in users:
        user.balance -= split_amount_per_user

    db.session.commit()

    return jsonify({'message': 'Split created successfully'}), 201
class SplitHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    num_users = db.Column(db.Integer, nullable=False)
    
    def __repr__(self):
        return f'<SplitHistory {self.id} by User {self.user_id}>'

@app.route('/split_history', methods=['GET'])
def split_history(): 
    current_user_id = get_jwt_identity()
    
    splits = SplitHistory.query.filter_by(user_id=current_user_id).all()

    split_list = []
    for split in splits:
        split_data = {
            'split_id': split.id,
            'total_amount': split.total_amount,
            'num_users': split.num_users,
            
        }
        split_list.append(split_data)

    return jsonify({'history': split_list}), 200
@app.route('/create_group', methods=['POST'])
def create_group():
    
    data = request.json
    group_name = data.get('group_name')
    member_ids = data.get('members')  
    new_group = Group(name=group_name)
    members = User.query.filter(User.id.in_(member_ids)).all()
    new_group.members.extend(members)
    db.session.add(new_group)
    db.session.commit()

    return jsonify({'message': 'Group created successfully'}), 201
@app.route('/groups', methods=['GET']) 
def list_groups():
    current_user_id = get_jwt_identity()  

    
    user = User.query.get(current_user_id)
    groups = user.groups if user else []

    
    group_list = [{'group_id': group.id, 'group_name': group.name} for group in groups]

    return jsonify({'groups': group_list}), 200
@app.route('/share_split', methods=['POST'])
def share_split():
    
    data = request.json
    split_id = data.get('split_id')
    
    split = Split.query.get(split_id)
    if not split:
        return jsonify({'error': 'Split not found'}), 404
    participants = [user.username for user in split.users]
    description = split.description if split.description else "No description provided."

    share_message = f"Split ID: {split.id}\n"
    share_message += f"Total Amount: {split.total_amount}\n"
    share_message += f"Split Description: {description}\n"
    share_message += f"Participants: {', '.join(participants)}\n"   
    return jsonify({'message': share_message}), 200
@app.route('/search_splits', methods=['GET'])
def search_splits():

    search_query = request.args.get('query')

    matching_splits = Split.query.filter(Split.description.ilike(f'%{search_query}%')).all()

    
    split_list = [{'split_id': split.id, 'description': split.description} for split in matching_splits]

    return jsonify({'splits': split_list}), 200
@app.route('/search_users', methods=['GET'])
def search_users():
    
    search_query = request.args.get('query')

    
    matching_users = User.query.filter(User.username.ilike(f'%{search_query}%')).all()

    user_list = [{'user_id': user.id, 'username': user.username} for user in matching_users]

    return jsonify({'users': user_list}), 200
def to_dict(self):
        return {
            'id': self.id,
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat(),
        }
@app.route('/notifications', methods=['GET'])
def get_notifications():
    user_id = get_jwt_identity() 
    notifications = Notification.query.filter_by(user_id=user_id).all()
    return jsonify({'notifications': [notif.to_dict() for notif in notifications]}), 200
def create_notification(user_id, message):
    notification = Notification(user_id=user_id, message=message)
    db.session.add(notification)
    db.session.commit()
def perform_transaction(sender_id, receiver_id, amount):
    sender = User.query.get(sender_id)
    receiver = User.query.get(receiver_id)

    if not sender or not receiver:
        return False, 'Invalid sender or receiver ID'

    if sender.balance < amount:
        return False, 'Insufficient balance'
    sender.balance -= amount
    receiver.balance += amount 
    db.session.commit()
    return True, 'Transaction successful'

@app.route('/transaction', methods=['POST'])
def handle_transaction():
    data = request.json
    sender_id = data.get('sender_id')
    receiver_id = data.get('receiver_id')
    amount = data.get('amount')

    if not sender_id or not receiver_id or not amount:
        return jsonify({'error': 'Invalid data'}), 400

    success, message = perform_transaction(sender_id, receiver_id, amount)

    if success:
        return jsonify({'message': message}), 200
    else:
        return jsonify({'error': message}), 400
@app.route('/notifications/<int:notification_id>/mark_read', methods=['POST'])
def mark_notification_read(notification_id):
    notification = Notification.query.get(notification_id)
    if notification:
        notification.is_read = True
        db.session.commit()
        return jsonify({'message': 'Notification marked as read'}), 200
    else:
        return jsonify({'message': 'Notification not found'}), 404
if __name__ == '__main__':
        app.run(debug=True)
        










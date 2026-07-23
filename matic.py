from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
CORS(app, origins="*", allow_headers="*", methods=["GET", "POST", "OPTIONS", "DELETE", "PUT"])

# Database file for persistent storage
ORDERS_FILE = 'orders.json'

# Email Configuration (update with your email details)
EMAIL_CONFIG = {
    'sender_email': 'your-email@gmail.com',
    'sender_password': 'your-app-password',  # Use app-specific password for Gmail
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'enabled': False  # Set to True when you add email credentials
}

def load_orders():
    """Load orders from file"""
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_orders(orders):
    """Save orders to file"""
    with open(ORDERS_FILE, 'w') as f:
        json.dump(orders, f, indent=2)

def send_email(recipient_email, subject, body):
    """Send email notification"""
    if not EMAIL_CONFIG['enabled']:
        print(f"📧 Email disabled. Would send to: {recipient_email}")
        return True
    
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.starttls()
        server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
        server.send_message(msg)
        server.quit()
        print(f"✉️ Email sent to: {recipient_email}")
        return True
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False

# GCash Configuration
GCASH_MERCHANT_ID = "YOUR_GCASH_MERCHANT_ID"
GCASH_API_KEY = "YOUR_GCASH_API_KEY"
GCASH_SECRET_KEY = "YOUR_GCASH_SECRET_KEY"
GCASH_PHONE = "09306113595"
WEBSITE_URL = "http://localhost:8000"

# Admin password (change this!)
ADMIN_PASSWORD = "yooweediner"

@app.before_request
def before_request():
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, DELETE, PUT'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

@app.route('/create-gcash-payment', methods=['POST', 'OPTIONS'])
def create_gcash_payment():
    """Create a GCash payment link"""
    if request.method == 'OPTIONS':
        return '', 204
    try:
        data = request.json
        amount = data.get('amount')
        customer_name = data.get('customerName')
        phone = data.get('phone')
        
        # Generate unique reference number
        reference_number = f"YW-{datetime.now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(3).upper()}"
        
        gcash_payment_url = (
            f"https://www.gcash.com/pay?"
            f"merchantid={GCASH_MERCHANT_ID}&"
            f"amount={amount}&"
            f"reference={reference_number}&"
            f"description=Yoo-Wee%20Diner%20Order&"
            f"customer={customer_name}&"
            f"phone={phone}&"
            f"receiver={GCASH_PHONE}&"
            f"callback={WEBSITE_URL}/payment.html?payment=success"
        )
        
        return jsonify({
            'success': True,
            'paymentUrl': gcash_payment_url,
            'reference': reference_number
        })
        
    except Exception as e:
        print(f"Error creating GCash payment: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/save-order', methods=['POST', 'OPTIONS'])
def save_order():
    """Save completed order to database"""
    if request.method == 'OPTIONS':
        return '', 204
    try:
        data = request.json
        
        order = {
            'orderId': f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(2).upper()}",
            'customer': data.get('customer'),
            'items': data.get('items'),
            'total': data.get('total'),
            'paymentMethod': data.get('paymentMethod'),
            'status': data.get('status', 'confirmed'),
            'createdAt': datetime.now().isoformat()
        }
        
        # Load existing orders and add new one
        orders = load_orders()
        orders.append(order)
        save_orders(orders)
        
        # Send email notification
        customer_email = data.get('customer', {}).get('phone', 'unknown')
        customer_name = data.get('customer', {}).get('name', 'Valued Customer')
        customer_address = data.get('customer', {}).get('address', 'N/A')
        
        email_subject = f"Order Confirmation - {order['orderId']}"
        email_body = f"""
        <h2>Order Confirmed!</h2>
        <p>Hi {customer_name},</p>
        <p>Your Yoo-Wee Diner order has been confirmed!</p>
        <h3>Order Details:</h3>
        <ul>
            <li><strong>Order ID:</strong> {order['orderId']}</li>
            <li><strong>Total:</strong> ₱{order['total']}</li>
            <li><strong>Payment Method:</strong> {order['paymentMethod']}</li>
            <li><strong>Address:</strong> {customer_address}</li>
            <li><strong>Confirmed at:</strong> {order['createdAt']}</li>
        </ul>
        <p>Thank you for ordering from Yoo-Wee Diner!</p>
        """
        
        send_email(customer_email, email_subject, email_body)
        
        # Log order
        print(f"\n✓ Order Confirmed: {order['orderId']}")
        print(f"  Customer: {order['customer']['name']}")
        print(f"  Total: ₱{order['total']}")
        print(f"  Method: {order['paymentMethod']}\n")
        
        return jsonify({
            'success': True,
            'orderId': order['orderId'],
            'message': 'Order saved successfully'
        })
        
    except Exception as e:
        print(f"Error saving order: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/get-orders', methods=['GET'])
def get_orders():
    """Retrieve all orders"""
    try:
        password = request.args.get('admin_key')
        if password and password != ADMIN_PASSWORD:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        orders = load_orders()
        return jsonify({
            'success': True,
            'orders': orders,
            'total': len(orders)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/update-order/<order_id>', methods=['PUT', 'OPTIONS'])
def update_order(order_id):
    """Update order status"""
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        password = request.args.get('admin_key')
        if password != ADMIN_PASSWORD:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        data = request.json
        new_status = data.get('status')
        
        orders = load_orders()
        for order in orders:
            if order['orderId'] == order_id:
                order['status'] = new_status
                order['updatedAt'] = datetime.now().isoformat()
                save_orders(orders)
                return jsonify({'success': True, 'order': order})
        
        return jsonify({'success': False, 'error': 'Order not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/delete-order/<order_id>', methods=['DELETE', 'OPTIONS'])
def delete_order(order_id):
    """Delete an order"""
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        password = request.args.get('admin_key')
        if password != ADMIN_PASSWORD:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        orders = load_orders()
        orders = [o for o in orders if o['orderId'] != order_id]
        save_orders(orders)
        
        return jsonify({'success': True, 'message': 'Order deleted'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/gcash-webhook', methods=['POST'])
def gcash_webhook():
    """Handle GCash payment confirmation webhook"""
    try:
        data = request.json
        reference = data.get('reference')
        status = data.get('status')
        
        print(f"GCash Webhook - Reference: {reference}, Status: {status}")
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({'success': False}), 500

@app.route('/', methods=['GET'])
def home():
    """API Status"""
    return jsonify({
        'status': 'running',
        'service': 'Yoo-Wee Diner Payment Server',
        'version': '1.0',
        'endpoints': {
            'POST /create-gcash-payment': 'Create GCash payment link',
            'POST /save-order': 'Save order',
            'GET /get-orders': 'Get all orders',
            'PUT /update-order/<id>': 'Update order status',
            'DELETE /delete-order/<id>': 'Delete order'
        }
    })

if __name__ == '__main__':
    print("\n🍔 Yoo-Wee Diner Payment Server Running on http://localhost:5001")
    print("📁 Orders saved to: orders.json")
    print("🔑 Admin key: " + ADMIN_PASSWORD)
    app.run(debug=True, port=5001)

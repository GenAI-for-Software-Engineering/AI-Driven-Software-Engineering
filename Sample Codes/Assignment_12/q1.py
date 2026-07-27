import os
import json
from dotenv import load_dotenv
import streamlit as st

from langchain_groq import ChatGroq

# =========================
# ENV SETUP
# =========================
load_dotenv()
key = os.getenv("GROQ_API_KEY")

if not key:
    st.error("Missing GROQ_API_KEY")
    st.stop()

# =========================
# LLM SETUP
# =========================
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.2
)

# =========================
# STRATEGY PATTERNS
# =========================

class PaymentStrategy:
    def pay(self, amount):
        pass

class CardPayment(PaymentStrategy):
    def pay(self, amount):
        return f"Paid {amount} using CARD (Razorpay)"

class UPIPayment(PaymentStrategy):
    def pay(self, amount):
        return f"Paid {amount} using UPI (PhonePe)"

class BNPLPayment(PaymentStrategy):
    def pay(self, amount):
        return f"Paid {amount} using BNPL (Credit Approved)"


class NotificationStrategy:
    def send(self, message):
        pass

class EmailNotification(NotificationStrategy):
    def send(self, message):
        return f"Email sent: {message}"

class SMSNotification(NotificationStrategy):
    def send(self, message):
        return f"SMS sent: {message}"

class WhatsAppNotification(NotificationStrategy):
    def send(self, message):
        return f"WhatsApp sent: {message}"

# =========================
# VALIDATION LAYER
# =========================

class DecisionValidator:

    SUPPORTED_PAYMENTS = ["CARD", "UPI", "BNPL"]
    MAX_DISCOUNT = 30

    def validate(self, decision):
        validated = {}

        # Payment validation
        payment = decision.get("payment", "UPI")
        if payment not in self.SUPPORTED_PAYMENTS:
            payment = "UPI"
        validated["payment"] = payment

        # Discount validation
        discount = decision.get("discount", "0%")
        try:
            value = int(discount.replace("%", ""))
            if value > self.MAX_DISCOUNT:
                value = self.MAX_DISCOUNT
            validated["discount"] = f"{value}%"
        except:
            validated["discount"] = "0%"

        # Notification validation
        notif = decision.get("notification", "EMAIL")
        if notif not in ["EMAIL", "SMS", "WHATSAPP"]:
            notif = "EMAIL"
        validated["notification"] = notif

        # Confidence fallback
        confidence = decision.get("confidence", 0.5)
        if confidence < 0.5:
            validated["payment"] = "UPI"
            validated["notification"] = "EMAIL"

        return validated

# =========================
# FACTORY FUNCTIONS
# =========================

def get_payment_strategy(payment_type):
    if payment_type == "CARD":
        return CardPayment()
    elif payment_type == "UPI":
        return UPIPayment()
    elif payment_type == "BNPL":
        return BNPLPayment()
    return UPIPayment()

def get_notification_strategy(channel):
    if channel == "EMAIL":
        return EmailNotification()
    elif channel == "SMS":
        return SMSNotification()
    elif channel == "WHATSAPP":
        return WhatsAppNotification()
    return EmailNotification()

# =========================
# CORE SERVICE
# =========================

class OrderService:

    def __init__(self):
        self.validator = DecisionValidator()

    def place_order(self, customer, amount, preference):

        # -------- PROMPT (f-string SAFE) --------
        prompt = f"""
You are an AI decision engine for a multi-vendor e-commerce platform.

Your responsibilities:
1. Select optimal payment method
2. Suggest discount strategy
3. Choose notification channel
4. Provide confidence score (0 to 1)

Business Constraints:
- Payment methods allowed: CARD, UPI, BNPL
- Notification channels: EMAIL, SMS, WHATSAPP
- Discount should not exceed 50%
- Prefer safer/common methods if uncertain

STRICT RULES:
- Output MUST be valid JSON
- No explanation text
- No markdown
- No extra words

Output format:
{{
  "payment": "CARD or UPI or BNPL",
  "discount": "10%",
  "notification": "EMAIL or SMS or WHATSAPP",
  "confidence": 0.85
}}

Input:
Customer: {customer}
Amount: {amount}
Preference: {preference}

Return ONLY JSON.
"""

        print("\n========== PROMPT ==========\n")
        print(prompt)

        # -------- AI CALL --------
        response = llm.invoke(prompt)

        print("\n========== RAW RESPONSE ==========\n")
        print(response)

        print("\n========== CONTENT ==========\n")
        print(response.content)

        # -------- JSON PARSE --------
        try:
            cleaned = response.content.strip().replace("```json", "").replace("```", "")
            decision = json.loads(cleaned)

            print("\n========== PARSED JSON ==========\n")
            print(decision)

        except Exception as e:
            print("\n❌ JSON PARSE ERROR:", e)
            decision = {}

        # -------- VALIDATION --------
        validated = self.validator.validate(decision)

        # -------- EXECUTION --------
        payment_strategy = get_payment_strategy(validated["payment"])
        notification_strategy = get_notification_strategy(validated["notification"])

        payment_result = payment_strategy.pay(amount)
        notification_result = notification_strategy.send(
            f"Order placed with {validated['discount']} discount"
        )

        return {
            "ai_decision": decision,
            "validated_decision": validated,
            "payment": payment_result,
            "notification": notification_result
        }

# =========================
# STREAMLIT UI
# =========================

st.title("AI-Assisted E-Commerce System")

customer = st.text_input("Customer Name")
amount = st.number_input("Order Amount", min_value=1.0)
preference = st.text_input("User Preference")

if st.button("Place Order"):

    if not customer:
        st.warning("Please enter customer name")
        st.stop()

    service = OrderService()
    result = service.place_order(customer, amount, preference)

    st.subheader("AI Decision")
    st.json(result["ai_decision"])

    st.subheader("Validated Decision")
    st.json(result["validated_decision"])

    st.subheader("Execution Result")
    st.write(result["payment"])
    st.write(result["notification"])

import os
import json

from dotenv import load_dotenv
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from openai import OpenAI

from ai.tools.customers import get_customer
from ai.tools.ambulance import check_availability
from ai.tools.bookings import create_booking

load_dotenv()
client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

router = APIRouter(
    prefix="/api/ai",
    tags=["AI Assistant"]
)

class ChatMessage(BaseModel):
    role: str
    content: str

class AssistantRequest(BaseModel):
    messages: List[ChatMessage]

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_customer",
            "description": "Get customer information by customer ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "The unique ID of the customer."
                    }
                },
                "required": ["customer_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Check which ambulances are currently available.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },{
    "type": "function",
    "function": {
        "name": "create_booking",
        "description": "Create a new pending ambulance booking for an existing customer.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "The ID of the existing customer."
                },
                "patient_name": {
                    "type": "string",
                    "description": "The patient's name."
                },
                "patient_phone": {
                    "type": "string",
                    "description": "The patient's phone number."
                },
                "pickup_address": {
                    "type": "string",
                    "description": "The pickup location."
                },
                "dropoff_address": {
                    "type": "string",
                    "description": "The destination address."
                }
            },
            "required": [
                "customer_id",
                "patient_name",
                "patient_phone",
                "pickup_address",
                "dropoff_address"
            ]
        }
    }
}
]


messages = [
    {
        "role": "user",
        "content": "Show me customer information for 0f2d012d-2497-4248-92ae-61d29bd34383"
    }
]


@router.post("/assistant")
def assistant(request: AssistantRequest):

    messages = [
    {
        "role": "system",
        "content": """
You are an AI assistant for an Emergency Ambulance Dispatch System.

You can:
- find customer information
- check available ambulances
- create pending ambulance bookings

Important:
- Never assign or select a specific ambulance for a booking.
- Never tell the user that an ambulance has been booked unless create_booking successfully returns a booking.
- Ambulance availability does not mean that ambulance is assigned to the customer.
- New bookings are always created with pending status.
- Only the admin/dispatch system assigns an ambulance.
"""
    }
]

    messages.extend([
        message.model_dump()
        for message in request.messages
    ])

    while True:

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )

        message = response.choices[0].message

        if not message.tool_calls:
            return {
                "success": True,
                "answer": message.content
            }

        messages.append(message)

        for tool_call in message.tool_calls:

            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            if tool_name == "get_customer":

                result = get_customer(
                    customer_id=arguments["customer_id"]
                )

            elif tool_name == "check_availability":

                result = check_availability()

            elif tool_name == "create_booking":

                result = create_booking(
                    customer_id=arguments["customer_id"],
                    patient_name=arguments["patient_name"],
                    patient_phone=arguments["patient_phone"],
                    pickup_address=arguments["pickup_address"],
                    dropoff_address=arguments["dropoff_address"]
                )

            else:
                result = {
                    "success": False,
                    "error": "Unknown tool"
                }

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, default=str)
            })
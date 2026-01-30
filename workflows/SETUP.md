# Voice AI Receptionist - Setup Guide

This n8n workflow integrates Vapi (Voice AI) with Google Calendar to create an automated voice receptionist that can book, cancel, and reschedule appointments.

## Workflow Overview

```
Vapi Call -> Webhook -> Extract Intent -> Route by Intent
                                              |
            +----------------+----------------+----------------+
            |                |                |                |
        Book Appt      Cancel Appt     Reschedule       General Inquiry
            |                |                |                |
      Check Calendar   Find Existing   Find Existing    Return Greeting
            |           Appointments    Appointments          |
      Analyze Slots         |                |                |
            |          Delete Event    Update Event           |
     Can Book? ----+        |                |                |
       |     |     |        |                |                |
    Create  Suggest |   Slack Notify         |                |
    Event   Alts    |        |               |                |
       |            |        +-------+-------+----------------+
   Format Success   |                |
       |            |                |
  +----+----+       |                |
  |    |    |       |                |
Slack Airtable Gmail|                |
  |    |    |       |                |
  +----+----+-------+----------------+
                |
          Respond to Vapi
```

## Prerequisites

1. **n8n instance** (self-hosted or n8n.cloud)
2. **Vapi account** with an active phone number
3. **Google Cloud project** with Calendar API enabled
4. **Slack workspace** (optional - for notifications)
5. **Airtable base** (optional - for logging)
6. **Gmail account** (optional - for confirmations)

## Setup Instructions

### Step 1: Import the Workflow

1. Open your n8n instance
2. Go to **Workflows** > **Import from File**
3. Select `voice-ai-receptionist-vapi.json`
4. Click **Import**

### Step 2: Configure Credentials

#### Google Calendar OAuth2

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable **Google Calendar API**
4. Create OAuth 2.0 credentials:
   - Application type: Web application
   - Authorized redirect URI: `https://your-n8n-instance.com/rest/oauth2-credential/callback`
5. In n8n, create a new **Google Calendar OAuth2** credential
6. Enter your Client ID and Client Secret
7. Connect and authorize

#### Slack OAuth2 (Optional)

1. Create a [Slack App](https://api.slack.com/apps)
2. Add OAuth scopes: `chat:write`, `channels:read`
3. Install to your workspace
4. In n8n, create a **Slack OAuth2** credential
5. Update the Slack channel ID in the workflow nodes

#### Airtable Token (Optional)

1. Go to [Airtable Developer Hub](https://airtable.com/create/tokens)
2. Create a Personal Access Token with:
   - Scope: `data.records:write`
   - Access to your base
3. Create a base with a "Calls" table containing columns:
   - Caller Phone (Single line text)
   - Call ID (Single line text)
   - Intent (Single line text)
   - Message (Long text)
   - Appointment Start (Date)
   - Appointment ID (Single line text)
   - Status (Single select)
   - Timestamp (Date)
4. Update the base and table IDs in the workflow

#### Gmail OAuth2 (Optional)

1. Use the same Google Cloud project
2. Enable **Gmail API**
3. Create OAuth 2.0 credentials (or use existing)
4. In n8n, create a **Gmail OAuth2** credential
5. Update the `fromEmail` in the email node

### Step 3: Configure Vapi

1. Log into your [Vapi Dashboard](https://dashboard.vapi.ai/)
2. Create a new **Assistant** with these settings:

```json
{
  "name": "Receptionist",
  "model": {
    "provider": "openai",
    "model": "gpt-4",
    "systemPrompt": "You are a friendly and professional AI receptionist. Help callers book, cancel, or reschedule appointments. Extract the date and time they want from their request."
  },
  "voice": {
    "provider": "elevenlabs",
    "voiceId": "your-voice-id"
  },
  "serverUrl": "https://your-n8n-instance.com/webhook/vapi-webhook",
  "serverUrlSecret": "your-secret-key",
  "functions": [
    {
      "name": "book_appointment",
      "description": "Book a new appointment for the caller",
      "parameters": {
        "type": "object",
        "properties": {
          "date": {
            "type": "string",
            "description": "The requested date for the appointment"
          },
          "time": {
            "type": "string",
            "description": "The requested time for the appointment"
          }
        }
      }
    },
    {
      "name": "cancel_appointment",
      "description": "Cancel an existing appointment",
      "parameters": {
        "type": "object",
        "properties": {}
      }
    },
    {
      "name": "reschedule_appointment",
      "description": "Reschedule an existing appointment to a new time",
      "parameters": {
        "type": "object",
        "properties": {
          "new_date": {
            "type": "string",
            "description": "The new date for the appointment"
          },
          "new_time": {
            "type": "string",
            "description": "The new time for the appointment"
          }
        }
      }
    }
  ]
}
```

3. Assign a phone number to this assistant
4. Update the webhook URL to point to your n8n instance

### Step 4: Activate the Workflow

1. Review all nodes and update placeholder IDs:
   - `GOOGLE_CALENDAR_OAUTH_ID` - Your Google Calendar credential ID
   - `SLACK_OAUTH_ID` - Your Slack credential ID
   - `AIRTABLE_TOKEN_ID` - Your Airtable credential ID
   - `GMAIL_OAUTH_ID` - Your Gmail credential ID
   - `C07XXXXXXXXX` - Your Slack channel ID
   - `appXXXXXXXXXXXXXX` - Your Airtable base ID
   - `tblXXXXXXXXXXXXXX` - Your Airtable table ID
   - `your-email@gmail.com` - Your email address

2. Click **Save** and **Activate** the workflow

### Step 5: Test the Integration

1. Call your Vapi phone number
2. Request to book an appointment (e.g., "I'd like to book an appointment for tomorrow at 2pm")
3. Verify:
   - Calendar event is created
   - Slack notification is sent
   - Airtable record is created
   - Confirmation email is sent

## Customization

### Business Hours

Modify the `Analyze Availability` code node to restrict bookings to business hours:

```javascript
// Add after extracting requestedHour
const businessStart = 9;  // 9 AM
const businessEnd = 17;   // 5 PM

if (requestedHour < businessStart || requestedHour >= businessEnd) {
  return {
    can_book: false,
    error: 'outside_business_hours',
    message: `We're only available between ${businessStart}AM and ${businessEnd - 12}PM.`
  };
}
```

### Appointment Duration

Change the default 1-hour duration in the `Analyze Availability` node:

```javascript
const appointmentDuration = 30 * 60 * 1000; // 30 minutes
```

### Custom Responses

Edit the response messages in the Code nodes to match your brand voice.

## Troubleshooting

### Webhook Not Receiving Calls

1. Ensure the workflow is activated
2. Verify the webhook URL in Vapi matches your n8n instance
3. Check n8n logs for incoming requests
4. Test with a direct POST request using curl or Postman

### Calendar Events Not Creating

1. Verify Google Calendar OAuth is properly configured
2. Check the calendar ID (use "primary" for main calendar)
3. Ensure the OAuth token hasn't expired

### Slack Notifications Not Sending

1. Verify the Slack channel ID is correct
2. Ensure the bot is invited to the channel
3. Check OAuth scopes include `chat:write`

## Support

For issues with:
- **Vapi**: Visit [Vapi Documentation](https://docs.vapi.ai/)
- **n8n**: Visit [n8n Documentation](https://docs.n8n.io/)
- **This workflow**: Open an issue in this repository

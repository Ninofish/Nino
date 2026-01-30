# Nino - Voice AI Receptionist

An n8n workflow that creates an AI-powered voice receptionist using Vapi and Google Calendar integration.

## Features

- **Appointment Booking**: Callers can book appointments via voice
- **Calendar Integration**: Automatic Google Calendar event creation
- **Availability Checking**: Intelligent conflict detection with alternative suggestions
- **Appointment Cancellation**: Cancel existing appointments by phone
- **Appointment Rescheduling**: Move appointments to new time slots
- **Multi-channel Notifications**: Slack alerts for new bookings and cancellations
- **Data Logging**: Airtable integration for call tracking
- **Email Confirmations**: Automated Gmail confirmation emails

## How It Works

1. Caller dials your Vapi phone number
2. Vapi's AI assistant handles the conversation
3. When an intent is detected (book/cancel/reschedule), Vapi calls your n8n webhook
4. n8n processes the request:
   - Checks Google Calendar availability
   - Creates/updates/deletes calendar events
   - Sends Slack notifications
   - Logs to Airtable
   - Sends confirmation emails
5. Response is sent back to Vapi to continue the conversation

## Quick Start

1. Import `workflows/voice-ai-receptionist-vapi.json` into n8n
2. Configure your credentials (Google Calendar, Slack, Airtable, Gmail)
3. Set up your Vapi assistant with the webhook URL
4. Activate the workflow

See [workflows/SETUP.md](workflows/SETUP.md) for detailed setup instructions.

## Workflow Structure

```
workflows/
  voice-ai-receptionist-vapi.json  # Main n8n workflow
  SETUP.md                          # Setup documentation
```

## Requirements

- n8n (self-hosted or cloud)
- Vapi account with phone number
- Google Cloud project with Calendar API
- Slack workspace (optional)
- Airtable account (optional)
- Gmail account (optional)

## Intents Supported

| Intent | Description | Vapi Function |
|--------|-------------|---------------|
| Book | Schedule a new appointment | `book_appointment` |
| Cancel | Cancel existing appointment | `cancel_appointment` |
| Reschedule | Move appointment to new time | `reschedule_appointment` |
| General | Handle other inquiries | Default response |

## License

MIT

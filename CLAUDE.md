# CLAUDE.md - AI Assistant Guide for Nino

## Project Overview

Nino is a **Voice AI Receptionist** built as an n8n workflow. It uses Vapi (voice AI platform) integrated with Google Calendar to handle appointment scheduling, cancellation, and rescheduling through automated voice calls.

This is **not a traditional code project** — it is an automation-as-code project where the primary artifact is an n8n workflow JSON file.

## Repository Structure

```
Nino/
├── CLAUDE.md                                        # This file
├── README.md                                        # Project overview and quick start
└── workflows/
    ├── SETUP.md                                     # Detailed setup and configuration guide
    └── voice-ai-receptionist-vapi.json              # Main n8n workflow definition (25 nodes)
```

There are no source code directories, no package.json, no build system, and no test framework. The entire application logic lives inside the workflow JSON file.

## Technology Stack

| Layer               | Technology                          |
|---------------------|-------------------------------------|
| Automation Platform | n8n (self-hosted or n8n.cloud)      |
| Voice AI            | Vapi with OpenAI GPT-4             |
| Voice Provider      | ElevenLabs (via Vapi)              |
| Calendar            | Google Calendar API (OAuth2)        |
| Notifications       | Slack API (OAuth2)                  |
| Data Logging        | Airtable API (Personal Access Token)|
| Email               | Gmail API (OAuth2)                  |
| Custom Logic        | JavaScript (n8n Code nodes)         |

## Workflow Architecture

```
Vapi Call -> Webhook -> Extract Intent -> Route by Intent
                                              |
            +----------------+----------------+----------------+
            |                |                |                |
        Book Appt      Cancel Appt     Reschedule       General Inquiry
            |                |                |                |
      Check Calendar   Find Existing   Find Existing    Return Greeting
            |           Appointments    Appointments
      Analyze Slots         |                |
            |          Delete Event    Update Event
       Can Book?             |                |
        /     \              |                |
   Create    Suggest         |                |
   Event     Alts           |                |
       |                     |                |
  Slack / Airtable / Gmail   Slack Notify     |
       |                     |                |
       +---------------------+----------------+
                      |
                Respond to Vapi
```

### Supported Intents

| Intent                    | Vapi Function              | Actions                                       |
|---------------------------|----------------------------|-----------------------------------------------|
| Book appointment          | `book_appointment`         | Check calendar, create event, notify, log      |
| Cancel appointment        | `cancel_appointment`       | Find event, delete, notify, log                |
| Reschedule appointment    | `reschedule_appointment`   | Find event, update time, notify                |
| General inquiry           | (default)                  | Return greeting/help message                   |

### Key Workflow Nodes (25 total)

- **Trigger**: Vapi Webhook — receives incoming voice call data
- **Routing**: Switch node routes by intent (`book_appointment`, `cancel_appointment`, `reschedule_appointment`)
- **Calendar Operations**: Google Calendar nodes for create/read/update/delete
- **Availability Logic**: JavaScript Code node (`Analyze Availability`) with date parsing and conflict detection
- **Data Extraction**: JavaScript Code node (`Clean Email & Extract Info`) with regex-based email/phone extraction
- **Notifications**: Slack nodes for booking and cancellation alerts
- **Logging**: Airtable node for call record creation
- **Email**: Gmail node for HTML confirmation emails
- **Response**: `Respond to Webhook` node returns JSON to Vapi for speech synthesis

## Development Workflow

### Making Changes

1. **Workflow modifications**: Import the JSON into an n8n instance, make changes via the n8n UI, then export the updated workflow JSON back to `workflows/voice-ai-receptionist-vapi.json`
2. **Documentation updates**: Edit `README.md` or `workflows/SETUP.md` directly
3. **Code node changes**: JavaScript logic in Code nodes can be edited in the n8n UI or directly in the JSON file (look for nodes with `type: "n8n-nodes-base.code"`)

### Testing

There is no automated test suite. Testing is manual:

1. Call the Vapi phone number
2. Request an appointment action (e.g., "Book an appointment for tomorrow at 2pm")
3. Verify: Google Calendar event created, Slack notification sent, Airtable record logged, confirmation email sent

### Deployment

1. Import `workflows/voice-ai-receptionist-vapi.json` into an n8n instance
2. Configure OAuth2 credentials for Google Calendar, Slack, Gmail, and Airtable token
3. Replace placeholder IDs in workflow nodes (see `workflows/SETUP.md` Step 4)
4. Configure Vapi assistant with the n8n webhook URL
5. Activate the workflow

## Key Conventions

### Workflow JSON Structure

- The workflow JSON uses n8n's standard format with `nodes`, `connections`, and `settings` top-level keys
- Node names use descriptive titles (e.g., "Check Calendar Availability", "Format Success Response")
- Node types follow n8n naming: `n8n-nodes-base.webhook`, `n8n-nodes-base.code`, `n8n-nodes-base.googleCalendar`, etc.

### Credential Placeholders

The workflow JSON contains placeholder credential IDs that must be replaced during setup:

- `GOOGLE_CALENDAR_OAUTH_ID`
- `SLACK_OAUTH_ID`
- `AIRTABLE_TOKEN_ID`
- `GMAIL_OAUTH_ID`
- `C07XXXXXXXXX` (Slack channel ID)
- `appXXXXXXXXXXXXXX` (Airtable base ID)
- `tblXXXXXXXXXXXXXX` (Airtable table ID)
- `your-email@gmail.com` (sender email)

### JavaScript Code Nodes

Custom logic is embedded in n8n Code nodes within the workflow JSON. Key logic:

- **Date/time parsing**: Supports natural language ("tomorrow", day names like "Monday") and specific times ("2pm", "10:30am"). Defaults to 10 AM when time is not specified.
- **Conflict detection**: Checks a 14-day calendar window for overlapping events
- **Alternative suggestions**: When a requested slot is taken, suggests nearby available times
- **Contact extraction**: Regex-based extraction of email addresses and phone numbers from speech transcription

### Customization Points

- **Business hours**: Modify the `Analyze Availability` Code node to restrict booking windows
- **Appointment duration**: Change duration constant in the `Analyze Availability` node (default: 1 hour)
- **Response messages**: Edit text in Code nodes to match brand voice
- **Notification channels**: Update Slack channel IDs or add additional notification targets

## Important Notes for AI Assistants

- **No build or lint commands exist.** Do not attempt to run `npm install`, `npm run build`, or similar commands.
- **The workflow JSON is the application.** Treat `workflows/voice-ai-receptionist-vapi.json` as the primary artifact. Changes to application logic require modifying this file or re-exporting from n8n.
- **Credentials are never stored in the repository.** All authentication is configured through the n8n UI. Never add secrets or credentials to any file.
- **The workflow JSON is machine-generated.** When editing it directly, preserve the n8n JSON structure (node IDs, connection references, position coordinates). Prefer making changes through n8n's UI and re-exporting when possible.
- **Timezone handling is limited.** The current implementation uses the n8n instance's local time. Be aware of this when modifying date/time logic.
- **Optional integrations**: Slack, Airtable, and Gmail are optional. The core booking flow only requires Google Calendar.

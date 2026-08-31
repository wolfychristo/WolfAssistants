from fastapi import APIRouter

# Create API router and mount versioned sub-routers here as they are implemented
api_router = APIRouter()

# Routers
from . import contacts as contacts_router
from . import meetings as meetings_router
from . import emails as emails_router  # Re-enabled emails router
from . import auth as auth_router
from . import email_settings as email_settings_router
from . import diagnostics as diagnostics_router
from . import otp as otp_router
from . import secure_otp as secure_otp_router
from . import simon as wolfy_router
from . import chat_sessions as chat_sessions_router
from . import security_monitoring as security_router
from . import monitoring as monitoring_router
from . import individual_user_debug as debug_router
from . import gemini_monitoring as gemini_router
from . import gemini_keys as gemini_keys_router
from . import tier_info as tier_info_router
from . import tier_upgrade as tier_upgrade_router
from . import referrals as referrals_router
from . import admin as admin_router
from . import admin_auth as admin_auth_router
from . import admin_user_management as admin_user_mgmt_router
from . import tax as tax_router
from . import user_feedback as user_feedback_router
from . import todos as todos_router
from . import deliverability as deliverability_router
from . import extension as extension_router
from . import scraped_leads as scraped_leads_router
from . import invoice_clients as invoice_clients_router
from . import sales_agent as sales_agent_router
from . import prospects as prospects_router
from . import replies as replies_router
from . import command_center as command_center_router
from app.api.workflow import router as workflow_router

api_router.include_router(contacts_router.router, prefix="/contacts", tags=["contacts"])
api_router.include_router(meetings_router.router, prefix="/meetings", tags=["meetings"])
api_router.include_router(emails_router.router, prefix="/emails", tags=["emails"])  # Re-enabled
api_router.include_router(workflow_router, prefix="/workflow", tags=["workflow"])
api_router.include_router(auth_router.router, prefix="/auth", tags=["auth"])
api_router.include_router(email_settings_router.router, prefix="/email-settings", tags=["email-settings"])
api_router.include_router(diagnostics_router.router, prefix="/diagnostics", tags=["diagnostics"])
api_router.include_router(otp_router.router, prefix="/otp", tags=["otp"])
api_router.include_router(secure_otp_router.router, prefix="/secure-otp", tags=["secure-otp"])
api_router.include_router(wolfy_router.router, prefix="/wolfy", tags=["wolfy"])
api_router.include_router(chat_sessions_router.router, prefix="/chat", tags=["chat-sessions"])
api_router.include_router(security_router.router, prefix="/security", tags=["security-monitoring"])
api_router.include_router(monitoring_router.router, prefix="/monitoring", tags=["monitoring"])
api_router.include_router(debug_router.router, prefix="/debug", tags=["individual-user-debug"])
api_router.include_router(gemini_router.router, prefix="/gemini", tags=["gemini-monitoring"])
api_router.include_router(gemini_keys_router.router, prefix="/gemini-keys", tags=["gemini-keys"])
api_router.include_router(tier_info_router.router, prefix="/tier", tags=["tier-info"])
api_router.include_router(tier_upgrade_router.router, prefix="/tier", tags=["tier-upgrade"])
api_router.include_router(referrals_router.router, prefix="/referrals", tags=["referrals"])
api_router.include_router(admin_auth_router.router, prefix="/admin-auth", tags=["admin-auth"])
api_router.include_router(admin_router.router, prefix="/admin", tags=["admin"])
api_router.include_router(admin_user_mgmt_router.router, prefix="/admin", tags=["admin-user-management"])
api_router.include_router(tax_router.router, prefix="/tax", tags=["tax"])
api_router.include_router(user_feedback_router.router, prefix="/user-feedback", tags=["user-feedback"])
api_router.include_router(todos_router.router, prefix="/todos", tags=["todos"])
api_router.include_router(deliverability_router.router, prefix="/deliverability", tags=["deliverability"])
api_router.include_router(extension_router.router, prefix="/extension", tags=["extension"])
api_router.include_router(scraped_leads_router.router, prefix="/scraped-leads", tags=["scraped-leads"])
api_router.include_router(invoice_clients_router.router, prefix="/invoice-clients", tags=["invoice-clients"])
api_router.include_router(sales_agent_router.router, prefix="/sales-agent", tags=["sales-agent"])
api_router.include_router(prospects_router.router, prefix="/prospects", tags=["prospects"])
api_router.include_router(replies_router.router, prefix="/replies", tags=["replies"])
api_router.include_router(command_center_router.router, prefix="/command-center", tags=["command-center"])



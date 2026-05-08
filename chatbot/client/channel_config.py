import os
from dataclasses import dataclass
from typing import List, Literal


@dataclass
class ChannelConfig:
    """Configuration for a specific channel."""
    prompt_id: str
    tools: List[str]
    response_format: Literal["streaming", "complete"]


# Channel configurations
CHANNEL_CONFIGS = {
    "web": ChannelConfig(
        prompt_id="Prompt-11" if os.getenv("TRIAL_ENABLED") == "true" else "Prompt-6",
        tools=[
            "get_knowledge_base",
            "check_lead",
            # "create_enquiry_lead",
            # "create_complete_lead",
            # "update_lead",
            # "send_email",   
            "check_seat_availability"
        ],
        response_format="streaming"
    ),
    "whatsapp": ChannelConfig(
        # prompt_id="Prompt-12" if os.getenv("TRIAL_ENABLED") == "true" else "Prompt-3",
        prompt_id="Prompt-3",
        tools=[
            "get_knowledge_base",
            "check_senderid",      # For automatic first-message lookup
            "check_lead",          # For manual lookup if user provides new info
            # "check_whatsapp_lead", # Redundant/Commented out in server
            "create_lead",
            "update_lead",
            "send_brochure",
            # "send_whatsapp_document",
            "check_seat_availability"
        ],
        response_format="complete"
    ),
    "instagram": ChannelConfig(
        # prompt_id="Prompt-13" if os.getenv("TRIAL_ENABLED") == "true" else "Prompt-7",
        prompt_id="Prompt-7",
        tools=[
            "get_knowledge_base",
            "check_senderid",
            "check_lead",
            "create_social_media_lead",
            "update_lead",
            "check_seat_availability"
        ] + (["send_email"] if os.getenv("TRIAL_ENABLED") == "true" else []),
        response_format="complete"
    ),
     "facebook": ChannelConfig(
        # prompt_id="Prompt-13" if os.getenv("TRIAL_ENABLED") == "true" else "Prompt-7",
        prompt_id="Prompt-7",
        tools=[
            "get_knowledge_base",
            "check_senderid",
            "check_lead",
            "create_social_media_lead",
            "update_lead",
            "check_seat_availability"
        ] + (["send_email"] if os.getenv("TRIAL_ENABLED") == "true" else []),
        response_format="complete"
    ),
    "whatsapp_counselor": ChannelConfig(
        prompt_id="Prompt-10",
        tools=[
            "search_crm",
            "batch_crm_operations",
            "get_knowledge_base",
        ],
        response_format="complete"
    ),
    "whatsapp_counselor_manager": ChannelConfig(
        prompt_id="Prompt-10",
        tools=[
            "search_crm",
            "batch_crm_operations",
            "get_knowledge_base",
            "get_subordinate_counselors",
        ],
        response_format="complete"
    )
}


def get_channel_config(channel: str) -> ChannelConfig:
    """
    Get configuration for a specific channel.
    Falls back to web config if channel not found.
    
    Args:
        channel: Channel identifier (web, whatsapp, etc.)
        
    Returns:
        ChannelConfig for the specified channel
    """
    return CHANNEL_CONFIGS.get(channel.lower(), CHANNEL_CONFIGS["web"])


def get_available_channels() -> List[str]:
    """Get list of all configured channels."""
    return list(CHANNEL_CONFIGS.keys())

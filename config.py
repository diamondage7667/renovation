"""Agent Configuration File.

This file should be customized based on the agent specifications to control
the behavior of the template.
"""

##################################################
####            LLM Settings                ####
##################################################

# Model Settings - using environment variable with fallback for compatibility
CHAT_MODEL_ID = "gemini-2.5-flash-lite"
CHAT_TEMPERATURE = 0.7


##################################################
####             Agent Context              ####
##################################################
# Set current location here
LOCATION = "San Francisco, California"

##################################################
####        Agent Prompt                   ####
##################################################

# Customizable agent prompt - defines the agent's role and purpose
AGENT_PROMPT = "You are a helpful and efficient home renovation and repair agent. Your primary goal is to gather all necessary information from callers to schedule a contractor visit. You need to collect the caller's name, details of the renovation or repair, the property address, available day and time for the contractor, and their phone number. Additionally, you must categorize the renovation/repair type from a predefined list (e.g., Roofing, Stairs, Flooring, HVAC, Electrical, Plumbing, Painting, Landscaping, Kitchen Remodel, Bathroom Remodel, General Repair). If the user provides a category not on this list, try to find the closest match or ask for clarification. Be polite, clear, and ensure all required information is obtained."

##################################################
#### Initial Message                          ####
##################################################
# This message is sent by the agent to the user when the call is started.
INITIAL_MESSAGE = "Hello! I'm here to help you with your home renovation or repair needs. To get started, could I please get your name?"

#!/usr/bin/env python3
"""
AGNTCY Multi-Agent Development Console
=====================================

A comprehensive development and testing interface for the multi-agent customer service platform.

Features:
- Interactive chatbot client for end-user simulation
- Real-time agent metrics and performance monitoring
- Conversation trace viewer with decision trees
- Mock API status and health monitoring
- System configuration and testing tools

Usage:
    streamlit run console/app.py --server.port 8080

Requirements:
    pip install streamlit plotly pandas requests websockets

Author: AGNTCY Multi-Agent Platform
Version: 1.0.0
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import json
import time
from datetime import datetime, timedelta
import asyncio
import websockets
from typing import Dict, List, Any, Optional
import uuid
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import project modules
try:
    from shared.models import CustomerMessage, Intent, Sentiment, Priority
    from shared.utils import setup_logging, load_config
    from shared.factory import get_factory
except ImportError as e:
    st.error(f"Failed to import project modules: {e}")
    st.info("Make sure you're running from the project root directory")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="AGNTCY Development Console",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS matching USER-INTERFACE-DESIGN-THEME.md
st.markdown("""
<style>
    /* Import Google Fonts: Michroma for headings, Montserrat for body text */
    @import url('https://fonts.googleapis.com/css2?family=Michroma&family=Montserrat:wght@400;500;600;700&display=swap');

    /* Theme base colors from USER-INTERFACE-DESIGN-THEME.md */
    :root {
        --primary-background: #18232B;
        --foreground-background: #243340;
        --text-color: #EEEEEE;
        --heading-color: #FFFFFF;
        --link-color: #FFFFFF;
        --link-hover: #CC2222;
        --border-color: #555555;
        --border-width: 1px;
    }

    /* Dark theme base */
    .stApp {
        background-color: var(--primary-background);
        color: var(--text-color);
        font-family: 'Montserrat', sans-serif;
        font-size: 15px;
    }

    /* Sidebar theme */
    .css-1d391kg {
        background-color: var(--foreground-background);
    }

    /* Main content area */
    .main .block-container {
        background-color: var(--primary-background);
        color: var(--text-color);
        font-family: 'Montserrat', sans-serif;
    }

    /* Header styling with Michroma font */
    .main-header {
        font-family: 'Michroma', sans-serif;
        font-size: 2.5rem;
        font-weight: bold;
        color: var(--heading-color);
        text-align: center;
        margin-bottom: 2rem;
    }

    /* All headings use Michroma font */
    h1, h2, h3 {
        font-family: 'Michroma', sans-serif;
        color: var(--heading-color);
    }

    h4, h5, h6 {
        font-family: 'Montserrat', sans-serif;
        color: var(--heading-color);
    }

    /* Metric cards with theme colors */
    .metric-card {
        background-color: var(--foreground-background);
        padding: 1rem;
        border-radius: 0.5rem;
        border: var(--border-width) solid var(--border-color);
        color: var(--text-color);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
    }

    /* Agent status indicators */
    .agent-status {
        padding: 0.5rem;
        border-radius: 0.25rem;
        margin: 0.25rem 0;
        color: var(--text-color);
        font-weight: 500;
    }
    .status-healthy {
        background-color: #2e7d32;
        color: #c8e6c9;
        border: 1px solid #4caf50;
    }
    .status-warning {
        background-color: #f57c00;
        color: #fff3e0;
        border: 1px solid #ff9800;
    }
    .status-error {
        background-color: #d32f2f;
        color: #ffcdd2;
        border: 1px solid #f44336;
    }

    /* Chat message styling */
    .chat-message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.5rem;
        border: var(--border-width) solid var(--border-color);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        font-family: 'Montserrat', sans-serif;
    }
    .user-message {
        background-color: #1a237e;
        margin-left: 2rem;
        color: #e3f2fd;
        border-left: 4px solid #3f51b5;
    }
    .agent-message {
        background-color: #1b5e20;
        margin-right: 2rem;
        color: #e8f5e8;
        border-left: 4px solid #4caf50;
    }
    .agent-message.status-error {
        background-color: #b71c1c;
        color: #ffebee;
        border-left: 4px solid #f44336;
    }
    .agent-message.status-warning {
        background-color: #e65100;
        color: #fff3e0;
        border-left: 4px solid #ff9800;
    }

    /* Trace step styling */
    .trace-step {
        border-left: 3px solid var(--link-hover);
        padding-left: 1rem;
        margin: 0.5rem 0;
        background-color: var(--foreground-background);
        border-radius: 0.25rem;
        color: var(--text-color);
    }

    /* Streamlit component overrides */
    .stSelectbox > div > div {
        background-color: var(--foreground-background);
        color: var(--text-color);
        border: var(--border-width) solid var(--border-color);
    }

    .stTextInput > div > div > input {
        background-color: var(--foreground-background);
        color: var(--text-color);
        border: var(--border-width) solid var(--border-color);
        font-family: 'Montserrat', sans-serif;
        font-size: 15px;
    }

    .stTextArea > div > div > textarea {
        background-color: var(--foreground-background);
        color: var(--text-color);
        border: var(--border-width) solid var(--border-color);
        font-family: 'Montserrat', sans-serif;
        font-size: 15px;
    }

    /* Buttons with link hover color */
    .stButton > button {
        background-color: var(--link-hover);
        color: var(--link-color);
        border: none;
        border-radius: 0.25rem;
        padding: 0.5rem 1rem;
        font-weight: 500;
        font-family: 'Montserrat', sans-serif;
        transition: opacity 0.3s;
    }

    .stButton > button:hover {
        opacity: 0.8;
        color: var(--link-color);
    }

    /* Metrics and dataframes */
    .stDataFrame {
        background-color: var(--foreground-background);
        color: var(--text-color);
        border: var(--border-width) solid var(--border-color);
    }

    .stMetric {
        background-color: var(--foreground-background);
        padding: 1rem;
        border-radius: 0.5rem;
        border: var(--border-width) solid var(--border-color);
    }

    .stMetric > div {
        color: var(--text-color);
    }

    .stMetric [data-testid="metric-container"] {
        background-color: var(--foreground-background);
        border: var(--border-width) solid var(--border-color);
        padding: 1rem;
        border-radius: 0.5rem;
    }

    /* Expander styling */
    .streamlit-expanderHeader {
        background-color: var(--foreground-background);
        color: var(--text-color);
        border: var(--border-width) solid var(--border-color);
    }

    .streamlit-expanderContent {
        background-color: var(--foreground-background);
        color: var(--text-color);
        border: var(--border-width) solid var(--border-color);
    }

    /* Info boxes */
    .stInfo {
        background-color: #0d47a1;
        color: #e3f2fd;
        border: 1px solid #1976d2;
    }

    .stSuccess {
        background-color: #1b5e20;
        color: #e8f5e8;
        border: 1px solid #4caf50;
    }

    .stWarning {
        background-color: #e65100;
        color: #fff3e0;
        border: 1px solid #ff9800;
    }

    .stError {
        background-color: #b71c1c;
        color: #ffebee;
        border: 1px solid #f44336;
    }

    /* Sidebar styling */
    .css-1d391kg .stSelectbox > div > div {
        background-color: var(--foreground-background);
        color: var(--text-color);
    }

    /* Form styling */
    .stForm {
        background-color: var(--foreground-background);
        border: var(--border-width) solid var(--border-color);
        border-radius: 0.5rem;
        padding: 1rem;
    }

    /* Code blocks */
    .stCode {
        background-color: var(--primary-background);
        color: var(--text-color);
        border: var(--border-width) solid var(--border-color);
        font-family: 'Courier New', monospace;
    }

    /* Spinner */
    .stSpinner {
        color: var(--link-hover);
    }

    /* Tables */
    .dataframe {
        background-color: var(--foreground-background);
        color: var(--text-color);
        font-family: 'Montserrat', sans-serif;
    }

    .dataframe th {
        background-color: var(--foreground-background);
        color: var(--heading-color);
        border: var(--border-width) solid var(--border-color);
        font-weight: 600;
    }

    .dataframe td {
        background-color: var(--foreground-background);
        color: var(--text-color);
        border: var(--border-width) solid var(--border-color);
    }

    /* Plotly chart backgrounds */
    .js-plotly-plot .plotly .modebar {
        background-color: var(--foreground-background);
    }

    /* Ensure all text has proper contrast and font */
    * {
        color: var(--text-color);
        font-family: 'Montserrat', sans-serif;
    }

    p, span, div, label {
        color: var(--text-color);
        font-family: 'Montserrat', sans-serif;
        font-size: 15px;
    }

    /* Links */
    a {
        color: var(--link-color);
        text-decoration: none;
    }

    a:hover {
        color: var(--link-hover);
    }

    /* Override any remaining light backgrounds */
    .element-container {
        background-color: transparent;
    }

    /* Quick message buttons */
    .stButton > button[kind="secondary"] {
        background-color: var(--foreground-background);
        color: var(--text-color);
        border: var(--border-width) solid var(--border-color);
    }

    .stButton > button[kind="secondary"]:hover {
        background-color: var(--primary-background);
        color: var(--link-hover);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []
if 'current_session_id' not in st.session_state:
    st.session_state.current_session_id = str(uuid.uuid4())
if 'agent_metrics' not in st.session_state:
    st.session_state.agent_metrics = {}
if 'system_traces' not in st.session_state:
    st.session_state.system_traces = []

class ConsoleAPI:
    """API client for interacting with the AGNTCY system."""
    
    def __init__(self):
        self.config = self._load_config()
        self.base_urls = {
            'shopify': 'http://localhost:8001',
            'zendesk': 'http://localhost:8002', 
            'mailchimp': 'http://localhost:8003',
            'google_analytics': 'http://localhost:8004',
            'grafana': 'http://localhost:3001',
            'clickhouse': 'http://localhost:8123'
        }
        
    def _load_config(self) -> Dict[str, Any]:
        """Load system configuration."""
        try:
            return load_config()
        except Exception as e:
            return {
                'agent_topic': 'console-agent',
                'log_level': 'INFO',
                'slim_endpoint': 'localhost:46357'
            }
    
    def check_service_health(self, service: str) -> Dict[str, Any]:
        """Check health status of a service."""
        try:
            url = f"{self.base_urls.get(service)}/health"
            response = requests.get(url, timeout=5)
            return {
                'status': 'healthy' if response.status_code == 200 else 'error',
                'response_time': response.elapsed.total_seconds(),
                'details': response.json() if response.status_code == 200 else response.text
            }
        except requests.exceptions.RequestException as e:
            return {
                'status': 'error',
                'response_time': None,
                'details': str(e)
            }
    
    def get_mock_api_metrics(self) -> Dict[str, Any]:
        """Retrieve metrics from mock APIs."""
        metrics = {}
        for service in ['shopify', 'zendesk', 'mailchimp', 'google_analytics']:
            try:
                url = f"{self.base_urls[service]}/metrics"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    metrics[service] = response.json()
                else:
                    metrics[service] = {'error': f"HTTP {response.status_code}"}
            except Exception as e:
                metrics[service] = {'error': str(e)}
        
        # Also get real agent metrics if available
        try:
            from console.agntcy_integration import get_integration
            integration = get_integration()
            agent_metrics = integration.get_agent_metrics()
            
            # Convert AgentMetrics objects to dictionaries
            for agent_name, agent_metric in agent_metrics.items():
                metrics[f"agent_{agent_name}"] = {
                    'total_requests': agent_metric.total_requests,
                    'success_rate': agent_metric.successful_requests / max(agent_metric.total_requests, 1),
                    'avg_latency_ms': agent_metric.avg_latency_ms,
                    'total_cost_usd': agent_metric.total_cost_usd,
                    'last_updated': agent_metric.last_updated.isoformat()
                }
        except Exception as e:
            metrics['agent_metrics_error'] = str(e)
        
        return metrics
    
    def send_message_to_agents(self, message: str, session_id: str) -> Dict[str, Any]:
        """Send a message through the agent system."""
        # This integrates with the real AGNTCY system via agntcy_integration
        try:
            from console.agntcy_integration import get_integration
            integration = get_integration()
            
            # Use asyncio to run the async method
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    integration.send_customer_message(message, session_id)
                )
                return result
            finally:
                loop.close()
                
        except Exception as e:
            # Fallback to mock response if integration fails
            intent = self._classify_intent_simple(message)
            mock_response = self._generate_contextual_response(message, intent)
            
            return {
                'success': True,
                'session_id': session_id,
                'message_id': str(uuid.uuid4()),
                'response': mock_response,
                'intent': intent,
                'confidence': 0.85,
                'processing_time_ms': 1200,
                'agents_involved': ['console-fallback'],
                'error': f"Integration error: {str(e)}"
            }
    
    def _generate_contextual_response(self, message: str, intent: str) -> str:
        """Generate contextual responses based on intent and Phase 2 coffee business."""
        message_lower = message.lower()
        
        if intent == 'product_comparison':
            if 'yirgacheffe' in message_lower and 'sidamo' in message_lower:
                return """Great question! Both are exceptional Ethiopian single origins with distinct characteristics:

**Ethiopian Yirgacheffe:**
- **Flavor Profile**: Bright citrus, floral notes, wine-like acidity
- **Processing**: Typically washed, highlighting clean, bright flavors
- **Body**: Light to medium, tea-like
- **Best For**: Pour-over methods (V60, Chemex), light roast lovers

**Ethiopian Sidamo:**
- **Flavor Profile**: Fruity, berry notes, chocolate undertones
- **Processing**: Often natural/dry processed, more fruit-forward
- **Body**: Medium, more rounded than Yirgacheffe
- **Best For**: French press, espresso, medium roast preferences

For brewing, I'd recommend a medium-fine grind with 200°F water. The Yirgacheffe really shines in a V60 pour-over, while Sidamo is fantastic as espresso or French press.

Which brewing method do you prefer? I can give you more specific recommendations!"""
            
        elif intent == 'product_info':
            return """I'd love to help you learn about our coffee! We specialize in single-origin beans with detailed tasting notes and brewing guides.

Our current featured coffees include Ethiopian, Colombian, and Guatemalan origins, each with unique flavor profiles. 

What specific aspect interests you most - origin, roast level, or brewing recommendations?"""
            
        elif intent == 'brewing_advice':
            return """I'm excited to help improve your brewing! Here are some key tips:

**General Guidelines:**
- **Grind**: Medium-fine for pour-over, coarse for French press
- **Water Temp**: 195-205°F (just off boiling)
- **Ratio**: 1:15 to 1:17 (coffee to water)
- **Time**: 4-6 minutes total brew time

**For V60 Pour-Over:**
1. 30g coffee, 500g water
2. 30-second bloom with 60g water
3. Slow, circular pours every 30 seconds
4. Total brew time: 4-5 minutes

What brewing method are you using? I can give you more specific guidance!"""
            
        elif intent == 'order_status':
            return """Hi! I'd be happy to help track your order.

For the most up-to-date information, I'll need to look up your specific order details. Your order should have shipped within 1-2 business days of placement.

If you have your order number handy, I can give you detailed tracking information. Most orders arrive within 3-5 business days via USPS Priority Mail.

What's your order number or the email address you used for your purchase?"""
            
        elif intent == 'product_recommendation':
            if 'starbucks' in message_lower:
                return """Perfect! If you enjoy Starbucks, I'd recommend starting with our medium roast single origins - they'll give you more complexity while still being familiar.

**Great Starting Points:**
- **Colombian Huila**: Chocolate and caramel notes, similar body to Pike Place
- **Brazilian Santos**: Nutty, smooth, great for everyday drinking
- **Guatemalan Antigua**: Rich, full-bodied with chocolate undertones

These are all approachable but will show you the difference that fresh, single-origin coffee can make. 

Are you looking for something for drip coffee, or do you have an espresso machine?"""
            else:
                return """I'd love to help you find the perfect coffee! To give you the best recommendation, could you tell me:

- Do you prefer light, medium, or dark roasts?
- What brewing method do you use most?
- Any flavor preferences (fruity, chocolatey, nutty)?
- Is this for daily drinking or special occasions?

Based on your preferences, I can suggest some of our most popular single origins!"""
                
        elif intent == 'return_request':
            return """I'm sorry to hear you're having an issue with your order! We want to make this right.

**Our Return Policy:**
- 30-day return window from delivery
- Orders under $50 can be auto-approved for refund
- Original packaging preferred but not required

For quality issues or defects, we'll process an immediate replacement or refund.

Could you tell me more about the issue? Was it a quality problem, wrong item, or just not what you expected? I'll get this resolved quickly for you."""
            
        elif intent == 'shipping_question':
            return """Here's our shipping information:

**Processing Time:** 1-2 business days
**Shipping Method:** USPS Priority Mail (1-3 business days)
**Free Shipping:** Orders over $35
**Tracking:** Provided via email once shipped

**Delivery Areas:**
- Continental US: 3-5 business days
- Alaska/Hawaii: 5-7 business days
- We don't currently ship internationally

Orders placed before 2 PM EST ship the same day (Monday-Friday).

Do you have a specific delivery date you need to meet? We also offer expedited shipping options!"""
            
        elif intent == 'bulk_inquiry':
            return """Great to hear from a business customer! We offer special pricing for bulk orders and office subscriptions.

**Business Benefits:**
- Volume discounts starting at 5+ bags
- Flexible delivery schedules
- Dedicated account management
- Custom roast profiles available

For orders over 10 bags or ongoing office needs, I'd like to connect you with our sales team who can create a custom package.

How many people are you looking to serve, and how often would you need deliveries?"""
            
        else:
            return """Thanks for reaching out! I'm here to help with any questions about our coffee, orders, or brewing advice.

**I can help you with:**
- Product information and recommendations
- Order status and tracking
- Brewing tips and techniques
- Returns and exchanges
- Bulk orders and business accounts

What can I assist you with today?"""
    
    def _classify_intent_simple(self, message: str) -> str:
        """Simple intent classification for fallback."""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['order', 'tracking', 'shipped', 'delivery', 'status']):
            return 'order_status'
        elif any(word in message_lower for word in ['yirgacheffe', 'sidamo', 'ethiopian', 'origin', 'difference', 'compare', 'versus', 'vs']):
            return 'product_comparison'
        elif any(word in message_lower for word in ['product', 'coffee', 'blend', 'roast', 'bean', 'flavor', 'taste']):
            return 'product_info'
        elif any(word in message_lower for word in ['return', 'refund', 'exchange', 'defect']):
            return 'return_request'
        elif any(word in message_lower for word in ['brew', 'grind', 'extraction', 'v60', 'pour', 'french press', 'espresso']):
            return 'brewing_advice'
        elif any(word in message_lower for word in ['gift', 'recommend', 'suggestion', 'beginner', 'starbucks']):
            return 'product_recommendation'
        elif any(word in message_lower for word in ['shipping', 'delivery', 'when', 'how long']):
            return 'shipping_question'
        elif any(word in message_lower for word in ['bulk', 'wholesale', 'business', 'office', 'discount']):
            return 'bulk_inquiry'
        else:
            return 'general_inquiry'
    
    def get_conversation_traces(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieve conversation traces for a session."""
        try:
            from console.agntcy_integration import get_integration
            integration = get_integration()
            
            traces = integration.get_conversation_traces(session_id)
            
            # Convert ConversationTrace objects to dictionaries
            trace_dicts = []
            for trace in traces:
                trace_dicts.append({
                    'timestamp': trace.start_time,
                    'agent': trace.agent_name,
                    'action': trace.action_type,
                    'input': trace.inputs.get('message', str(trace.inputs)),
                    'output': trace.outputs.get('result', str(trace.outputs)),
                    'confidence': trace.metadata.get('confidence', 1.0),
                    'latency_ms': trace.duration_ms,
                    'cost_usd': trace.metadata.get('cost_usd', 0.001),
                    'success': trace.success
                })
            
            return trace_dicts
            
        except Exception as e:
            # Return mock traces if integration fails
            return [
                {
                    'timestamp': datetime.now() - timedelta(seconds=30),
                    'agent': 'intent-classifier',
                    'action': 'classify_intent',
                    'input': 'Where is my order?',
                    'output': 'order_status',
                    'confidence': 0.95,
                    'latency_ms': 150,
                    'cost_usd': 0.0003,
                    'success': True
                },
                {
                    'timestamp': datetime.now() - timedelta(seconds=29),
                    'agent': 'knowledge-retrieval',
                    'action': 'search_orders',
                    'input': 'order_status + customer_context',
                    'output': 'Order #12345 found',
                    'confidence': 1.0,
                    'latency_ms': 800,
                    'cost_usd': 0.0015,
                    'success': True
                },
                {
                    'timestamp': datetime.now() - timedelta(seconds=28),
                    'agent': 'response-generator',
                    'action': 'generate_response',
                    'input': 'order_status + order_data',
                    'output': 'Your order shipped yesterday...',
                    'confidence': 0.92,
                    'latency_ms': 1200,
                    'cost_usd': 0.0025,
                    'success': True
                }
            ]

# Initialize API client
@st.cache_resource
def get_console_api():
    return ConsoleAPI()

api = get_console_api()

# Main application
def main():
    """Main application entry point."""
    
    # Header
    st.markdown('<h1 class="main-header">🤖 AGNTCY Development Console</h1>', unsafe_allow_html=True)
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Select Page",
        ["🏠 Dashboard", "💬 Chat Interface", "📊 Agent Metrics", "🔍 Trace Viewer", "⚙️ System Status"]
    )
    
    # Page routing
    if page == "🏠 Dashboard":
        show_dashboard()
    elif page == "💬 Chat Interface":
        show_chat_interface()
    elif page == "📊 Agent Metrics":
        show_agent_metrics()
    elif page == "🔍 Trace Viewer":
        show_trace_viewer()
    elif page == "⚙️ System Status":
        show_system_status()

def show_dashboard():
    """Show main dashboard with system overview."""
    st.header("System Overview")
    
    # System health metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Active Sessions", "3", "↑ 1")
    with col2:
        st.metric("Messages Today", "127", "↑ 23")
    with col3:
        st.metric("Avg Response Time", "1.8s", "↓ 0.3s")
    with col4:
        st.metric("Automation Rate", "78%", "↑ 2%")
    
    # Recent activity
    st.subheader("Recent Activity")
    
    # Mock recent conversations
    recent_data = pd.DataFrame({
        'Time': pd.date_range(start='2026-01-23 09:00', periods=10, freq='15min'),
        'Session': [f"session_{i}" for i in range(1, 11)],
        'Intent': ['order_status', 'product_info', 'return_request', 'shipping_question', 'brewing_advice'] * 2,
        'Response Time (s)': [1.2, 2.1, 1.8, 0.9, 2.3, 1.5, 1.9, 1.1, 2.0, 1.7],
        'Escalated': [False, False, True, False, False, False, True, False, False, False]
    })
    
    # Response time chart
    fig = px.line(recent_data, x='Time', y='Response Time (s)', 
                  title='Response Time Trend',
                  color_discrete_sequence=['#64b5f6'])
    fig.update_layout(
        height=300,
        plot_bgcolor='#1e1e1e',
        paper_bgcolor='#1e1e1e',
        font_color='#fafafa',
        title_font_color='#64b5f6'
    )
    fig.update_xaxes(gridcolor='#444', color='#fafafa')
    fig.update_yaxes(gridcolor='#444', color='#fafafa')
    st.plotly_chart(fig, use_container_width=True)
    
    # Intent distribution
    intent_counts = recent_data['Intent'].value_counts()
    fig_pie = px.pie(values=intent_counts.values, names=intent_counts.index,
                     title='Intent Distribution',
                     color_discrete_sequence=px.colors.qualitative.Set3)
    fig_pie.update_layout(
        height=300,
        plot_bgcolor='#1e1e1e',
        paper_bgcolor='#1e1e1e',
        font_color='#fafafa',
        title_font_color='#64b5f6'
    )
    st.plotly_chart(fig_pie, use_container_width=True)

def show_chat_interface():
    """Show interactive chat interface for testing."""
    st.header("Interactive Chat Interface")
    
    # Session controls
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.info(f"Session ID: {st.session_state.current_session_id}")
    with col2:
        if st.button("New Session"):
            st.session_state.current_session_id = str(uuid.uuid4())
            st.session_state.conversation_history = []
            st.rerun()
    with col3:
        persona = st.selectbox("Test Persona", 
                              ["Sarah (Enthusiast)", "Mike (Convenience)", "Jennifer (Gift)", "David (Business)"])
    
    # Chat interface
    st.subheader("Conversation")
    
    # Display conversation history
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.conversation_history:
            if msg['type'] == 'user':
                st.markdown(f"""
                <div class="chat-message user-message">
                    <strong>You:</strong> {msg['content']}
                    <br><small>{msg['timestamp']}</small>
                </div>
                """, unsafe_allow_html=True)
            else:
                escalation_indicator = "🔴 ESCALATED" if msg.get('escalation_needed', False) else ""
                error_indicator = "⚠️ ERROR" if msg.get('error', False) else ""
                agents_info = f"Agents: {', '.join(msg.get('agents_involved', []))}" if msg.get('agents_involved') else ""
                
                # Choose appropriate styling based on message type
                message_class = "agent-message"
                if msg.get('error', False):
                    message_class += " status-error"
                elif msg.get('escalation_needed', False):
                    message_class += " status-warning"
                
                st.markdown(f"""
                <div class="chat-message {message_class}">
                    <strong>AI Assistant:</strong> {msg['content']} {escalation_indicator} {error_indicator}
                    <br><small>{msg['timestamp']} • {msg.get('processing_time', 'N/A')}s • Intent: {msg.get('intent', 'N/A')} • {agents_info}</small>
                </div>
                """, unsafe_allow_html=True)
    
    # Message input
    st.subheader("Send Message")
    
    # Quick test messages based on persona
    persona_messages = {
        "Sarah (Enthusiast)": [
            "What's the difference between your Ethiopian Yirgacheffe and Sidamo?",
            "My V60 extractions are bitter - what grind size do you recommend?",
            "Can you tell me about the processing method for this coffee?"
        ],
        "Mike (Convenience)": [
            "Where's my order?",
            "Can I change my subscription to decaf?",
            "What's your strongest coffee?"
        ],
        "Jennifer (Gift)": [
            "What's a good coffee for someone who drinks Starbucks?",
            "Can you gift wrap this?",
            "What if they don't like it?"
        ],
        "David (Business)": [
            "Can we get a discount for monthly orders?",
            "What's your most popular office blend?",
            "We need 10 pounds delivered by Friday."
        ]
    }
    
    # Quick message buttons
    st.write("Quick Test Messages:")
    cols = st.columns(3)
    for i, msg in enumerate(persona_messages.get(persona, [])):
        with cols[i % 3]:
            if st.button(f"📝 {msg[:30]}...", key=f"quick_{i}"):
                send_message(msg)
    
    # Custom message input
    with st.form("message_form"):
        user_message = st.text_area("Type your message:", height=100)
        submitted = st.form_submit_button("Send Message")
        
        if submitted and user_message:
            send_message(user_message)

def send_message(message: str):
    """Send a message and get response from agents."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    # Add user message to history
    st.session_state.conversation_history.append({
        'type': 'user',
        'content': message,
        'timestamp': timestamp
    })
    
    # Send to agent system
    with st.spinner("Processing..."):
        response_data = api.send_message_to_agents(message, st.session_state.current_session_id)
    
    # Handle different response structures
    if not response_data.get('success', True):
        # Error case - create error response
        error_message = f"Sorry, I encountered an error: {response_data.get('error', 'Unknown error')}"
        agent_response = {
            'type': 'agent',
            'content': error_message,
            'timestamp': timestamp,
            'processing_time': 0,
            'intent': 'error',
            'confidence': 0,
            'escalation_needed': True,
            'agents_involved': ['error-handler'],
            'error': True
        }
    else:
        # Success case - extract response
        response_content = response_data.get('response', 'I apologize, but I was unable to generate a proper response.')
        
        agent_response = {
            'type': 'agent',
            'content': response_content,
            'timestamp': timestamp,
            'processing_time': response_data.get('processing_time_ms', 0) / 1000,  # Convert ms to seconds
            'intent': response_data.get('intent', 'unknown'),
            'confidence': response_data.get('confidence', 0),
            'escalation_needed': response_data.get('escalation_needed', False),
            'agents_involved': response_data.get('agents_involved', []),
            'error': False
        }
    
    # Add agent response to history
    st.session_state.conversation_history.append(agent_response)
    
    # Store trace data if available
    if 'trace_id' in response_data:
        traces = api.get_conversation_traces(st.session_state.current_session_id)
        st.session_state.system_traces.extend(traces)
    
    st.rerun()

def show_agent_metrics():
    """Show detailed agent performance metrics."""
    st.header("Agent Performance Metrics")
    
    # Refresh button
    if st.button("🔄 Refresh Metrics"):
        st.cache_data.clear()
    
    # Mock agent performance data
    agents = ['Intent Classifier', 'Knowledge Retrieval', 'Response Generator', 'Escalation', 'Analytics']
    
    # Performance metrics table
    metrics_data = pd.DataFrame({
        'Agent': agents,
        'Requests': [145, 142, 138, 23, 145],
        'Avg Latency (ms)': [150, 800, 1200, 300, 100],
        'Success Rate (%)': [98.6, 97.2, 96.4, 100.0, 99.3],
        'Cost ($)': [0.045, 0.213, 0.345, 0.069, 0.029],
        'Errors': [2, 4, 5, 0, 1]
    })
    
    st.dataframe(metrics_data, use_container_width=True)
    
    # Performance charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Latency comparison
        fig_latency = px.bar(metrics_data, x='Agent', y='Avg Latency (ms)',
                           title='Average Latency by Agent',
                           color='Avg Latency (ms)',
                           color_continuous_scale='Viridis')
        fig_latency.update_layout(
            plot_bgcolor='#1e1e1e',
            paper_bgcolor='#1e1e1e',
            font_color='#fafafa',
            title_font_color='#64b5f6'
        )
        fig_latency.update_xaxes(gridcolor='#444', color='#fafafa')
        fig_latency.update_yaxes(gridcolor='#444', color='#fafafa')
        st.plotly_chart(fig_latency, use_container_width=True)
    
    with col2:
        # Cost breakdown
        fig_cost = px.pie(metrics_data, values='Cost ($)', names='Agent',
                         title='Cost Distribution by Agent',
                         color_discrete_sequence=px.colors.qualitative.Set3)
        fig_cost.update_layout(
            plot_bgcolor='#1e1e1e',
            paper_bgcolor='#1e1e1e',
            font_color='#fafafa',
            title_font_color='#64b5f6'
        )
        st.plotly_chart(fig_cost, use_container_width=True)
    
    # Detailed agent status
    st.subheader("Agent Status Details")
    
    for i, agent in enumerate(agents):
        with st.expander(f"{agent} Details"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Requests/Hour", metrics_data.iloc[i]['Requests'])
                st.metric("Success Rate", f"{metrics_data.iloc[i]['Success Rate (%)']}%")
            
            with col2:
                st.metric("Avg Latency", f"{metrics_data.iloc[i]['Avg Latency (ms)']} ms")
                st.metric("Total Cost", f"${metrics_data.iloc[i]['Cost ($)']:.3f}")
            
            with col3:
                st.metric("Error Count", metrics_data.iloc[i]['Errors'])
                status = "🟢 Healthy" if metrics_data.iloc[i]['Errors'] < 3 else "🟡 Warning"
                st.write(f"Status: {status}")

def show_trace_viewer():
    """Show conversation trace viewer."""
    st.header("Conversation Trace Viewer")
    
    # Session selector
    sessions = list(set([trace.get('session_id', st.session_state.current_session_id) 
                        for trace in st.session_state.system_traces]))
    if not sessions:
        sessions = [st.session_state.current_session_id]
    
    selected_session = st.selectbox("Select Session", sessions)
    
    # Trace timeline
    if st.session_state.system_traces:
        st.subheader("Trace Timeline")
        
        # Create timeline visualization
        trace_df = pd.DataFrame(st.session_state.system_traces)
        if not trace_df.empty:
            fig = px.timeline(trace_df, 
                            x_start='timestamp', 
                            x_end='timestamp',
                            y='agent',
                            color='agent',
                            title='Agent Execution Timeline')
            fig.update_layout(
                plot_bgcolor='#1e1e1e',
                paper_bgcolor='#1e1e1e',
                font_color='#fafafa',
                title_font_color='#64b5f6'
            )
            fig.update_xaxes(gridcolor='#444', color='#fafafa')
            fig.update_yaxes(gridcolor='#444', color='#fafafa')
            st.plotly_chart(fig, use_container_width=True)
        
        # Detailed trace steps
        st.subheader("Trace Details")
        
        for i, trace in enumerate(st.session_state.system_traces):
            with st.expander(f"Step {i+1}: {trace['agent']} - {trace['action']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Input:**")
                    st.code(trace['input'])
                    st.write("**Output:**")
                    st.code(trace['output'])
                
                with col2:
                    st.metric("Latency", f"{trace['latency_ms']} ms")
                    st.metric("Cost", f"${trace['cost_usd']:.4f}")
                    st.metric("Confidence", f"{trace['confidence']:.2f}")
                    st.write(f"**Timestamp:** {trace['timestamp']}")
    else:
        st.info("No traces available. Send some messages in the Chat Interface to generate traces.")

def show_system_status():
    """Show system and service status."""
    st.header("System Status")
    
    # Service health checks
    st.subheader("Service Health")
    
    services = ['shopify', 'zendesk', 'mailchimp', 'google_analytics']
    
    # Check all services
    health_data = []
    for service in services:
        health = api.check_service_health(service)
        health_data.append({
            'Service': service.title(),
            'Status': health['status'],
            'Response Time': f"{health['response_time']:.3f}s" if health['response_time'] else "N/A",
            'Details': str(health['details'])[:100] + "..." if len(str(health['details'])) > 100 else str(health['details'])
        })
    
    # Display service status
    for service_data in health_data:
        status_class = f"status-{service_data['Status']}"
        st.markdown(f"""
        <div class="agent-status {status_class}">
            <strong>{service_data['Service']}</strong> - {service_data['Status'].upper()}
            <br>Response Time: {service_data['Response Time']}
            <br>Details: {service_data['Details']}
        </div>
        """, unsafe_allow_html=True)
    
    # Docker services status
    st.subheader("Docker Services")
    
    # This would integrate with docker-compose ps
    docker_services = [
        {'name': 'agntcy-nats', 'status': 'running', 'uptime': '2h 15m'},
        {'name': 'agntcy-slim', 'status': 'running', 'uptime': '2h 15m'},
        {'name': 'agntcy-clickhouse', 'status': 'running', 'uptime': '2h 15m'},
        {'name': 'agntcy-grafana', 'status': 'running', 'uptime': '2h 15m'},
        {'name': 'agntcy-mock-shopify', 'status': 'running', 'uptime': '2h 15m'},
        {'name': 'agntcy-mock-zendesk', 'status': 'running', 'uptime': '2h 15m'},
        {'name': 'agntcy-mock-mailchimp', 'status': 'running', 'uptime': '2h 15m'},
        {'name': 'agntcy-mock-google-analytics', 'status': 'running', 'uptime': '2h 15m'},
    ]
    
    docker_df = pd.DataFrame(docker_services)
    st.dataframe(docker_df, use_container_width=True)
    
    # System configuration
    st.subheader("System Configuration")
    
    config_info = {
        'AGNTCY SDK Version': '0.6.1',
        'Python Version': '3.14.0',
        'Docker Compose Version': '2.24.0',
        'Current Session ID': st.session_state.current_session_id,
        'Console Uptime': '2h 15m',
        'Total Messages Processed': '127'
    }
    
    for key, value in config_info.items():
        st.write(f"**{key}:** {value}")

if __name__ == "__main__":
    main()
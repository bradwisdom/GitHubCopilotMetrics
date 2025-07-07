# Understanding GitHub Copilot Model Reporting

## Why All Models Show as "Default"

In the GitHub Copilot metrics API, all model usage is reported as `"model": "default"` with `"is_custom_model": false` regardless of which specific AI model is powering the completion or chat response. This happens because:

1. The GitHub Copilot service abstracts away the underlying model details in its metrics reporting
2. The metrics API was designed before multi-model support was widely available
3. The "default" designation refers to the GitHub Copilot service itself, not the specific AI model

## Available Models vs. Reported Models

Even though your metrics show only "default" models, your organization does have access to multiple underlying AI models:

- **GitHub Copilot** (based on OpenAI models)
- **Claude models** (like Claude Sonnet 3.7 which you mentioned using)
- **Other models** configured for your organization

## How Model Selection Actually Works

When you use GitHub Copilot:

1. **In-editor completions** typically use the default OpenAI-based model
2. **Chat interactions** may use different models based on:
   - User selection in the chat interface
   - Query complexity and requirements
   - Organization policy settings

## Premium Requests

Your usage data shows "Premium requests: 9.3%", which indicates that some percentage of your queries are being routed to more advanced models. These premium requests still appear as "default" in the metrics despite potentially using models like Claude.

## How to Track Actual Model Usage

Since the metrics API doesn't differentiate between underlying models, you can:

1. **Review the premium request percentage** - Higher percentages often indicate more usage of advanced models
2. **Analyze performance patterns** - Different response patterns in completions may indicate different underlying models
3. **Survey team members** for their model selection habits in the chat interface

## Future Improvements

GitHub is continually improving their metrics reporting. Future versions of the API may include more detailed model attribution to help organizations better understand which specific AI models are being used.

#!/bin/bash
# Quick script to generate and open the research dashboard

echo "🔬 Generating research dashboard..."
python3 research_dashboard.py

if [ -f "research_dashboard.html" ]; then
    echo "📊 Opening dashboard in browser..."
    open research_dashboard.html
else
    echo "❌ Dashboard generation failed"
    exit 1
fi
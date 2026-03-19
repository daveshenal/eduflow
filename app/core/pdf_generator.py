"""
HTML to Stylish PDF Converter
Converts HTML content to a styled PDF document.
"""

import argparse
import logging
from pathlib import Path
import sys
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

def create_default_styles():
    """Create default CSS styles for better PDF appearance"""
    return """
@page { 
    size: A4; 
    margin: 2cm 2cm 3cm 2cm;
    
    @bottom-left {
        content: "© EduFlow Research Project | Confidential";
        margin-top: 30pt;
        margin-bottom: 25pt;
        padding: 0;
        font-size: 10pt;
        border-top: 0.5pt solid #333;
        width: 100%;
    }
    
    @bottom-right { 
        content: "Page " counter(page);
        margin-top: 30pt;
        margin-bottom: 25pt;
        padding: 0;
        font-size: 10pt;
        text-align: right;
        border-top: 0.5pt solid #333;
        width: 100%;
    }
    
    /* border-bottom: 1px solid #A3C; */
}

body { 
    font-family: 'Times New Roman'; 
    font-size: 12pt;
    line-height: 1.5;
    color: #222; 
    max-width: 100%; 
    margin: 0;
    padding: 0;
}

h1, h2, h3, h4, h5, h6 { 
    margin-top: 1.5em; 
    margin-bottom: 0.5em; 
    page-break-after: avoid; 
}

h1 { 
    font-size: 24pt;
    border-bottom: 0.5pt solid #222;
    padding-bottom: 1pt;
    text-transform: uppercase; 
}

h1:first-of-type {
    margin-top: 0.5em;
}

h2 { 
    font-size: 20pt;
}

h3 { 
    font-size: 16pt;
    color: #333; 
}

p { 
    margin-bottom: 1em;
    text-align: justify; 
}

table { 
    border-collapse: collapse; 
    width: 100%; 
    margin: 1em 0; 
    page-break-inside: avoid; 
}

th, td { 
    border: 1px solid #ddd; 
    padding: 8px;
    text-align: left; 
}

th { 
    background-color: #f2f2f2; 
    font-weight: bold; 
}

tr:nth-child(even) { 
    background-color: #f9f9f9; 
}

ul, ol { 
    padding-left: 40px;
}

li { 
    margin-bottom: 0.5em; 
}

a { 
    color: #333; 
    text-decoration: none; 
}

a:hover { 
    text-decoration: underline; 
}

.page-break { 
    page-break-before: always; 
}

.no-break { 
    page-break-inside: avoid; 
}
"""

def html_to_pdf(html_content, output_path, custom_css=None):
    """
    Convert HTML content to PDF with styling
    
    Args:
        html_content (str): HTML content to convert
        output_path (str): Path where PDF should be saved
        custom_css (str): Optional custom CSS styles
    """
    try:
        # Create font configuration
        font_config = FontConfiguration()
        
        # Prepare CSS styles
        default_styles = create_default_styles()
        if custom_css:
            combined_css = default_styles + "\n" + custom_css
        else:
            combined_css = default_styles
        
        # Create HTML document
        html_doc = HTML(string=html_content)
        
        # Create CSS document
        css_doc = CSS(string=combined_css, font_config=font_config)
        
        # Generate PDF
        html_doc.write_pdf(output_path, stylesheets=[css_doc], font_config=font_config)
        
        print(f"PDF successfully created: {output_path}")
        return True
        
    except Exception as e:
        print(f"Error creating PDF: {str(e)}")
        return False

def read_file(file_path):
    """Read content from file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {str(e)}")
        return None

async def create_pdf(doc_id: int, doc_content: str, output_dir: Path) -> str:
    """Create a PDF file for a single document.
    
    Args:
        doc_id: The ID of the document
        doc_content: The content text to include in the PDF
        output_dir: Directory where the PDF should be saved
        
    Returns:
        str: Path to the generated PDF file
        
    Raises:
        Exception: If PDF creation fails
    """
    try:
        pdf_filename = f"doc-{doc_id}.pdf"
        pdf_path = output_dir / pdf_filename
        
        # HTML wrapper for the content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Document {doc_id}</title>
        </head>
        <body>
            {doc_content}
        </body>
        </html>
        """
        
        # Create font configuration
        font_config = FontConfiguration()
        
        # Prepare CSS styles
        default_styles = create_default_styles()
        
        # Create HTML document
        html_doc = HTML(string=html_content)
        
        # Create CSS document
        css_doc = CSS(string=default_styles, font_config=font_config)
        
        html_doc = HTML(string=html_content)
        
        # Generate PDF
        html_doc.write_pdf(str(pdf_path), stylesheets=[css_doc], font_config=font_config)
        
        logging.info(f"Generated PDF: {pdf_path}")
        return str(pdf_path)
        
    except Exception as pdf_error:
        logging.error(f"Failed to create PDF for document {doc_id}: {pdf_error}")
        raise pdf_error

def main():
    parser = argparse.ArgumentParser(description='Convert HTML to stylish PDF')
    parser.add_argument('input', help='Input HTML file path or HTML string')
    parser.add_argument('-o', '--output', default='output.pdf', help='Output PDF file path')
    parser.add_argument('-c', '--css', help='Custom CSS file path for additional styling')
    parser.add_argument('-s', '--string', action='store_true', help='Treat input as HTML string instead of file path')
    
    args = parser.parse_args()
    
    # Get HTML content
    if args.string:
        html_content = args.input
    else:
        html_content = read_file(args.input)
        if html_content is None:
            sys.exit(1)
    
    # Get custom CSS if provided
    custom_css = None
    if args.css:
        custom_css = read_file(args.css)
        if custom_css is None:
            print("Warning: Could not read CSS file, proceeding without custom styles")
    
    # Convert to PDF
    success = html_to_pdf(html_content, args.output, custom_css)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    # Example usage when run directly
    if len(sys.argv) == 1:
        print("HTML to PDF Converter")
        print("=" * 50)
        print("\nUsage examples:")
        print("python html_to_pdf.py input.html -o output.pdf")
        print("python html_to_pdf.py -s '<h1>Hello World</h1>' -o hello.pdf")
        print("python html_to_pdf.py input.html -c styles.css -o styled.pdf")
        print("\nInstall dependencies:")
        print("pip install weasyprint")
        print("\nCreating sample HTML for demonstration...")
        
        # Create sample HTML
        sample_html = """
        <!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF Conversion Test</title>
</head>
<body>
    <h1>Project Status Report</h1>

<h2>Executive Summary</h2>
<p>The quarterly development cycle has been completed with significant progress across all major initiatives. Team productivity increased by 23% compared to the previous quarter.</p>

<h3>Key Achievements</h3>
<p>Our development team successfully delivered five major feature releases, resolved 127 bug reports, and improved system performance by 40%. The user experience overhaul received positive feedback from 89% of beta testers.</p>

<table>
<tr>
<th>Department</th>
<th>Completed Tasks</th>
<th>In Progress</th>
<th>Success Rate</th>
</tr>
<tr>
<td>Engineering</td>
<td>45</td>
<td>12</td>
<td>97.8%</td>
</tr>
<tr>
<td>Design</td>
<td>28</td>
<td>6</td>
<td>94.2%</td>
</tr>
<tr>
<td>Quality Assurance</td>
<td>156</td>
<td>23</td>
<td>96.1%</td>
</tr>
</table>

<h2>Technical Implementation Details</h2>
<p>The system architecture has been modernized to support scalable cloud deployment. Database optimization reduced query response times significantly.</p>

<h4>Performance Metrics</h4>
<p>Response time improvements were measured across different system components. Average page load time decreased from 3.2 seconds to 1.8 seconds.</p>

<ul>
<li>API endpoints optimized for better throughput</li>
<li>Database indexing strategies implemented</li>
<li>Caching mechanisms deployed across services</li>
<li>Load balancing configuration updated</li>
<li>Security protocols enhanced with multi-factor authentication</li>
</ul>

<h3>Development Milestones</h3>
<p>The team achieved several critical milestones ahead of schedule. Code review processes were streamlined, resulting in faster deployment cycles.</p>

<ol>
<li>Authentication system redesign completed</li>
<li>Payment processing integration tested</li>
<li>Mobile application beta version released</li>
<li>Data analytics dashboard launched</li>
<li>Third-party API connections established</li>
</ol>

<table>
<tr>
<th>Feature</th>
<th>Status</th>
<th>Launch Date</th>
<th>User Adoption</th>
</tr>
<tr>
<td>Advanced Search</td>
<td>Live</td>
<td>March 15</td>
<td>76%</td>
</tr>
<tr>
<td>Real-time Notifications</td>
<td>Beta</td>
<td>March 28</td>
<td>34%</td>
</tr>
<tr>
<td>Export Functionality</td>
<td>Development</td>
<td>April 10</td>
<td>N/A</td>
</tr>
</table>

<h2>Resource Allocation</h2>
<p>Budget utilization remained within approved limits while achieving stretch goals. Additional resources were allocated to critical path items.</p>

<h3>Team Structure</h3>
<p>Cross-functional teams worked collaboratively on integrated solutions. Knowledge sharing sessions improved overall team capability.</p>

<ul>
<li>Senior developers mentoring junior team members</li>
<li>Weekly technical presentations by different teams</li>
<li>Best practices documentation created and shared</li>
<li>Code pairing sessions increased collaboration</li>
</ul>

<h4>Training and Development</h4>
<p>Professional development initiatives supported career growth for team members. Certification programs were completed by 15 employees.</p>

<ol>
<li>Cloud architecture certification program</li>
<li>Agile methodology workshops conducted</li>
<li>Security awareness training completed</li>
<li>Modern JavaScript frameworks course</li>
<li>DevOps pipeline management training</li>
</ol>

<h2>Quality Assurance Results</h2>
<p>Comprehensive testing protocols ensured high-quality deliverables. Automated testing coverage increased to 87% across all modules.</p>

<table>
<tr>
<th>Test Type</th>
<th>Tests Executed</th>
<th>Pass Rate</th>
<th>Critical Bugs</th>
</tr>
<tr>
<td>Unit Tests</td>
<td>2,847</td>
<td>99.2%</td>
<td>0</td>
</tr>
<tr>
<td>Integration Tests</td>
<td>456</td>
<td>97.8%</td>
<td>2</td>
</tr>
<tr>
<td>End-to-End Tests</td>
<td>123</td>
<td>95.1%</td>
<td>1</td>
</tr>
</table>

<h3>Bug Resolution Timeline</h3>
<p>Issue tracking and resolution processes were optimized for faster turnaround. Average resolution time improved by 35%.</p>

<ul>
<li>Critical bugs resolved within 4 hours</li>
<li>High priority issues addressed within 24 hours</li>
<li>Medium priority fixes completed within one week</li>
<li>Low priority enhancements scheduled for next release</li>
</ul>

<h2>Customer Feedback Analysis</h2>
<p>User satisfaction surveys indicated high approval ratings for recent updates. Support ticket volume decreased by 28% following feature improvements.</p>

<h4>User Engagement Metrics</h4>
<p>Daily active users increased consistently throughout the reporting period. Feature adoption rates exceeded initial projections.</p>

<ol>
<li>Login frequency increased by 42%</li>
<li>Session duration extended by average 18 minutes</li>
<li>Feature utilization improved across all user segments</li>
<li>Mobile app downloads increased by 156%</li>
<li>Customer retention rate reached 94.3%</li>
</ol>

<h3>Support Statistics</h3>
<p>Customer support response times improved significantly with streamlined processes. Self-service options reduced routine inquiry volume.</p>

<table>
<tr>
<th>Month</th>
<th>Tickets Created</th>
<th>Tickets Resolved</th>
<th>Average Response Time</th>
</tr>
<tr>
<td>January</td>
<td>234</td>
<td>231</td>
<td>2.3 hours</td>
</tr>
<tr>
<td>February</td>
<td>198</td>
<td>195</td>
<td>1.8 hours</td>
</tr>
<tr>
<td>March</td>
<td>167</td>
<td>165</td>
<td>1.4 hours</td>
</tr>
</table>

<h2>Financial Performance</h2>
<p>Revenue targets were exceeded by 12% with controlled operational expenses. Investment in technology infrastructure yielded positive returns.</p>

<h3>Cost Optimization</h3>
<p>Operational efficiency improvements reduced overhead while maintaining service quality. Cloud migration resulted in 23% cost savings.</p>

<ul>
<li>Infrastructure costs reduced through optimization</li>
<li>Development tool consolidation saved licensing fees</li>
<li>Automated processes eliminated manual overhead</li>
<li>Energy-efficient hardware deployment completed</li>
</ul>

<h4>Revenue Growth Factors</h4>
<p>Multiple revenue streams contributed to overall growth. New product features attracted premium subscribers.</p>

<ol>
<li>Premium subscription tier launched successfully</li>
<li>Enterprise customer acquisitions increased</li>
<li>Partnership revenue streams established</li>
<li>International market expansion initiated</li>
<li>Add-on services monetization improved</li>
</ol>

<h2>Future Planning</h2>
<p>Strategic roadmap development focused on sustainable growth and innovation. Market analysis informed product development priorities.</p>

<h3>Next Quarter Objectives</h3>
<p>Ambitious but achievable goals were established for the upcoming period. Resource planning aligned with strategic initiatives.</p>

<table>
<tr>
<th>Initiative</th>
<th>Priority</th>
<th>Expected Completion</th>
<th>Resource Requirements</th>
</tr>
<tr>
<td>AI Integration</td>
<td>High</td>
<td>June 30</td>
<td>8 developers</td>
</tr>
<tr>
<td>Mobile App 2.0</td>
<td>High</td>
<td>July 15</td>
<td>6 developers</td>
</tr>
<tr>
<td>Analytics Platform</td>
<td>Medium</td>
<td>August 30</td>
<td>4 developers</td>
</tr>
</table>

<h4>Innovation Pipeline</h4>
<p>Research and development efforts focused on emerging technologies and user needs. Prototype development began for next-generation features.</p>

<ul>
<li>Machine learning algorithm improvements</li>
<li>Voice interface development</li>
<li>Blockchain integration research</li>
<li>Augmented reality feature exploration</li>
<li>Advanced security protocol implementation</li>
</ul>

<p>Report compiled by the Project Management Office. Data accurate as of March 31, 2024. Next quarterly review scheduled for July 1, 2024.</p>
</body>
</html>
        """
        
        # Convert sample HTML to PDF
        success = html_to_pdf(sample_html, "temp/docs/sample_output.pdf")
        
        if success:
            print("\nSample PDF created: temp/docss/sample_output.pdf")
            print("\nTo use with your own HTML:")
            print("python html_to_pdf.py your_file.html -o your_output.pdf")
    else:
        main()
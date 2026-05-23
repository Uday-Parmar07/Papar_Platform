from io import BytesIO
from typing import List, Dict

from jinja2 import Environment, BaseLoader
from weasyprint import HTML


PDF_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
	<head>
		<meta charset="utf-8" />
		<title>{{ title }}</title>
		<style>
			body { font-family: Arial, sans-serif; margin: 32px; }
			h1 { text-align: center; }
			.question { margin-bottom: 24px; }
			.meta { font-size: 12px; color: #555; margin-bottom: 8px; }
			.text { font-size: 14px; line-height: 1.4; }
		</style>
	</head>
	<body>
		<h1>{{ title }}</h1>
		{% for question in questions %}
		<div class="question">
			<div class="meta">{{ loop.index }}. {{ question.concept }} &mdash; {{ question.difficulty }}</div>
			<div class="text">{{ question.question }}</div>
		</div>
		{% endfor %}
	</body>
</html>
"""


def render_questions_pdf(title: str, questions: List[Dict[str, str]]) -> BytesIO:
		env = Environment(loader=BaseLoader())
		template = env.from_string(PDF_TEMPLATE)

		html_content = template.render(title=title, questions=questions)

		pdf_buffer = BytesIO()
		HTML(string=html_content).write_pdf(pdf_buffer)
		pdf_buffer.seek(0)

		return pdf_buffer

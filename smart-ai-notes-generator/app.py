import io
import json
import logging
import os
from datetime import datetime

from flask import Flask, jsonify, render_template, request, send_file
import google.generativeai as genai

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak
)

from api import Get_Ai_Api

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

GEMINI_API_KEY = Get_Ai_Api() # Enter api Key

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-3-flash-preview"

def get_model():
    return genai.GenerativeModel(
        MODEL_NAME,
        generation_config={
            "response_mime_type": "application/json",
            "temperature": 0.7
        }
    )

def clean_json(text):
    return (
        text.replace("```json", "")
        .replace("```", "")
        .strip()
    )

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/topics/explore", methods=["POST"])
def explore_topics():
    try:
        data = request.get_json()

        topic = data.get("topic", "").strip()

        if not topic:
            return jsonify({"error": "Topic is required"}), 400

        prompt = f"""
        You are an expert educator.

        Organize the topic "{topic}" into 4-6 logical groups.

        Return ONLY valid JSON:
        {{
          "mainTopic": "{topic}",
          "topicGroups": [
            {{
              "id": "group-1",
              "title": "Group Title",
              "subtopics": [
                {{
                  "id": "sub-1",
                  "title": "Subtopic",
                  "description": "Short description"
                }}
              ]
            }}
          ]
        }}
        """

        response = get_model().generate_content(prompt)

        result = json.loads(clean_json(response.text))

        return jsonify(result)

    except Exception as e:
        logger.exception("Explore topics failed")
        return jsonify({"error": str(e)}), 500

def detect_topic_type(topic):
    prompt = f"""
    Determine whether this topic is coding/programming related.

    Topic:
    "{topic}"

    Return ONLY valid JSON:
    {{
      "isCodeTopic": true,
      "reason": "short reason"
    }}
    """

    response = get_model().generate_content(prompt)

    return json.loads(clean_json(response.text))

@app.route("/api/notes/generate", methods=["POST"])
def generate_notes():
    try:
        data = request.get_json()

        main_topic = data.get("mainTopic")
        selected_topics = data.get("selectedTopics", [])

        analysis = detect_topic_type(main_topic)

        is_code_topic = analysis.get("isCodeTopic", False)

        code_instruction = ""

        if is_code_topic:
            code_instruction = """
            Include:
            - code examples
            - syntax explanations
            - debugging tips
            - best practices
            """

        prompt = f"""
        Create detailed educational slides.

        Main topic:
        {main_topic}

        Selected topics:
        {json.dumps(selected_topics)}

        {code_instruction}

        Return ONLY valid JSON:
        {{
          "mainTopic": "{main_topic}",
          "generatedAt": "{datetime.utcnow().isoformat()}",
          "isCodeTopic": {str(is_code_topic).lower()},
          "slides": [
            {{
              "id": "slide-1",
              "title": "Title",
              "slideType": "detail",
              "contentSections": [
                {{
                  "type": "text",
                  "title": "Concept",
                  "content": "Explanation"
                }},
                {{
                  "type": "code",
                  "language": "python",
                  "title": "Example",
                  "code": "print('hello')"
                }}
              ],
              "summary": "Summary",
              "flashNotes": ["Point 1", "Point 2"],
              "practiceQuestions": ["Question"]
            }}
          ]
        }}
        """

        response = get_model().generate_content(prompt)

        result = json.loads(clean_json(response.text))

        result["topicAnalysis"] = analysis

        return jsonify(result)

    except Exception as e:
        logger.exception("Generate notes failed")
        return jsonify({"error": str(e)}), 500

@app.route("/api/notes/download-pdf", methods=["POST"])
def download_pdf():
    try:
        data = request.get_json()

        buffer = io.BytesIO()

        doc = SimpleDocTemplate(buffer, pagesize=A4)

        styles = getSampleStyleSheet()

        story = []

        for slide in data.get("slides", []):

            story.append(
                Paragraph(
                    slide.get("title", "Untitled"),
                    styles["Heading1"]
                )
            )

            story.append(Spacer(1, 12))

            for section in slide.get("contentSections", []):

                if section["type"] == "text":
                    story.append(
                        Paragraph(
                            f"<b>{section['title']}</b><br/>{section['content']}",
                            styles["BodyText"]
                        )
                    )

                elif section["type"] == "code":
                    code_html = (
                        f"<font face='Courier'>"
                        f"{section['code'].replace(chr(10), '<br/>')}"
                        f"</font>"
                    )

                    story.append(
                        Paragraph(
                            f"<b>{section['title']}</b><br/>{code_html}",
                            styles["BodyText"]
                        )
                    )

                story.append(Spacer(1, 10))

            story.append(
                Paragraph(
                    f"<b>Summary:</b> {slide.get('summary', '')}",
                    styles["BodyText"]
                )
            )

            story.append(PageBreak())

        doc.build(story)

        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name="smart-notes.pdf",
            mimetype="application/pdf"
        )

    except Exception as e:
        logger.exception("PDF generation failed")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)

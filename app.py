#app.py

from flask import Flask, render_template, request, jsonify, redirect, url_for
import mysql.connector
import json
import os
from datetime import datetime
import subprocess
import pandas as pd
import plotly
import plotly.express as px
import plotly.graph_objects as go
import random

app = Flask(__name__)

# Database connection
db = mysql.connector.connect(
    host="localhost",
    port="3300",
    user="root",
    password="1234",
    database="name"
)
cursor = db.cursor(dictionary=True)

# Get all questions
cursor.execute("SELECT * FROM python_questions")
questions = cursor.fetchall()

# File to store answers and emotions
ANSWERS_FILE = 'answers.json'
EMOTIONS_FILE = 'emotions.json'

# Function to clear answers.json
def clear_answers_file():
    with open(ANSWERS_FILE, 'w') as f:
        json.dump([], f)

# Function to generate random emotions
def generate_random_emotions():
    emotions = {
        "happiness": random.uniform(0.2, 0.8),
        "sadness": random.uniform(0, 0.3),
        "anger": random.uniform(0, 0.2),
        "fear": random.uniform(0, 0.3),
        "surprise": random.uniform(0, 0.3),
        "disgust": random.uniform(0, 0.1)
    }
    # Normalize to ensure sum is 1
    total = sum(emotions.values())
    for key in emotions:
        emotions[key] /= total
    
    return emotions
@app.route('/test')
def index():
    clear_answers_file()
    return render_template('index.html', total_questions=len(questions))

@app.route('/')
def root():
    return redirect(url_for('home'))


@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/question/<int:id>')
def get_question(id):
    if 0 <= id < len(questions):
        return jsonify(questions[id])
    return jsonify({"error": "Question not found"}), 404

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    data = request.json
    question_id = data['question_id']
    answer = data['answer']
    
    if os.path.exists(ANSWERS_FILE):
        with open(ANSWERS_FILE, 'r') as f:
            answers = json.load(f)
    else:
        answers = []
    
    answers.append({
        "question_id": question_id,
        "question_text": questions[question_id]['question_text'],
        "answer": answer,
        "timestamp": datetime.now().isoformat()
    })
    
    with open(ANSWERS_FILE, 'w') as f:
        json.dump(answers, f, indent=2)
    
    return jsonify({"status": "success"})

@app.route('/end_test', methods=['POST'])
def end_test():
    # Generate random emotions and save to file
    emotions = generate_random_emotions()
    with open(EMOTIONS_FILE, 'w') as f:
        json.dump({"emotions": emotions}, f, indent=2)
    
    # Run gemini.py to generate scores
    subprocess.run(["python", "gemini.py"])
    return redirect(url_for('results'))

@app.route('/results')
def results():
    with open('report.json', 'r') as f:
        report_data = json.load(f)
    
    with open(EMOTIONS_FILE, 'r') as f:
        emotions_data = json.load(f)

    if isinstance(report_data, list):
        df = pd.DataFrame(report_data)
    else:
        df = pd.DataFrame([report_data])

    score_column = next((col for col in df.columns if 'score' in col.lower()), None)
    if score_column is None:
        df['score'] = 0
        score_column = 'score'
        print("Warning: No score column found in report data")

    technical_score = df[score_column].mean()
    emotion_score = emotions_data['emotions']['happiness'] * 5
    combined_score = (technical_score + emotion_score) / 2

    score_distribution = px.histogram(df, x=score_column, title='Technical Score Distribution',
                                      labels={score_column: 'Score', 'count': 'Frequency'},
                                      nbins=20, color_discrete_sequence=['#3366cc'])
    
    score_gauge = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = combined_score,
        title = {'text': "Combined Score"},
        domain = {'x': [0, 1], 'y': [0, 1]},
        gauge = {'axis': {'range': [0, 5]},
                 'bar': {'color': "#3366cc"},
                 'steps': [
                     {'range': [0, 2], 'color': "#ff9999"},
                     {'range': [2, 3.5], 'color': "#ffff99"},
                     {'range': [3.5, 5], 'color': "#99ff99"}]}
    ))

    emotions_df = pd.DataFrame(list(emotions_data['emotions'].items()), columns=['Emotion', 'Value'])
    emotions_pie = px.pie(emotions_df, values='Value', names='Emotion', title='Emotional State During Test',
                          color_discrete_sequence=px.colors.qualitative.Pastel)
    
    score_distribution_json = json.dumps(score_distribution, cls=plotly.utils.PlotlyJSONEncoder)
    score_gauge_json = json.dumps(score_gauge, cls=plotly.utils.PlotlyJSONEncoder)
    emotions_pie_json = json.dumps(emotions_pie, cls=plotly.utils.PlotlyJSONEncoder)

    emotion_analysis = []
    for emotion, value in emotions_data['emotions'].items():
        percentage = value * 100
        if emotion == 'fear' and percentage > 10:
            emotion_analysis.append(f"Your fear level was {percentage:.1f}%. Try some relaxation techniques before your next test.")
        elif emotion == 'happiness' and percentage < 30:
            emotion_analysis.append(f"Your happiness level was {percentage:.1f}%. Remember to stay positive during tests!")
        elif emotion == 'anger' and percentage > 15:
            emotion_analysis.append(f"Your anger level was {percentage:.1f}%. Try to manage frustration better in future tests.")
        elif emotion == 'surprise' and percentage > 20:
            emotion_analysis.append(f"You were surprised {percentage:.1f}% of the time. This might indicate you encountered unexpected questions.")

    performance_analysis = ""
    if technical_score < 2:
        performance_analysis += f"Your technical performance needs improvement. You scored {technical_score:.2f} out of 5. "
        performance_analysis += "Consider reviewing the following areas: basic syntax and programming concepts, "
        performance_analysis += "problem-solving strategies, and time management during the test. "
    elif 2 <= technical_score < 3.5:
        performance_analysis += f"You've shown a good understanding of the basics. Your technical score was {technical_score:.2f} out of 5. "
        performance_analysis += "To improve further, focus on: advanced programming concepts, efficiency in coding, "
        performance_analysis += "and tackling more complex problems. "
    else:
        performance_analysis += f"Excellent technical performance! You scored {technical_score:.2f} out of 5. "
        performance_analysis += "To maintain and enhance your skills: explore more advanced topics, "
        performance_analysis += "practice solving complex algorithmic problems, and consider mentoring others or contributing to open-source projects. "

    performance_analysis += "\nYour emotional state also played a role in your performance. "
    dominant_emotion = max(emotions_data['emotions'], key=emotions_data['emotions'].get)
    performance_analysis += f"Your dominant emotion was {dominant_emotion} at {emotions_data['emotions'][dominant_emotion]*100:.1f}%. "
    
    if emotions_data['emotions']['happiness'] > 0.5:
        performance_analysis += "Your high happiness level likely contributed positively to your performance. "
    elif emotions_data['emotions']['fear'] > 0.3:
        performance_analysis += "Your elevated fear levels may have impacted your performance. Consider stress-management techniques for future tests. "

    performance_analysis += f"\nYour combined score, taking into account both technical skills and emotional state, is {combined_score:.2f} out of 5."

    return render_template('results.html', 
                           report_data=report_data,
                           technical_score=technical_score,
                           emotion_score=emotion_score,
                           combined_score=combined_score,
                           score_distribution=score_distribution_json,
                           score_gauge=score_gauge_json,
                           emotions_pie=emotions_pie_json,
                           emotion_analysis=emotion_analysis,
                           performance_analysis=performance_analysis)

if __name__ == '__main__':
    app.run(debug=True)
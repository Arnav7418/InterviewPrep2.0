import json
import google.generativeai as genai
import os

# Configure the API key
genai.configure(api_key="AIzaSyAVVHuSg4HUzt3WRMve9YApI2uOYANH1rk")

# Load the answers from answers.json
with open('answers.json') as f:
    answers_data = json.load(f)

# Define the model generation configuration
generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
}

# Create the GenerativeModel instance
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
)

# Function to evaluate a single question-answer pair
def evaluate_answer(question, answer):
    prompt = f"""
    Evaluate the following answer to the given question. Assign a score out of 5, with 5 being the highest for a perfect answer.

    Question: {question}
    Answer: {answer}

    Scoring criteria:
    - Score 5: Perfect answer, fully addresses the question with correct implementation and formatting.
    - Score 4: Very good answer, minor mistakes or omissions.
    - Score 3: Good answer, partially correct with some errors or missing elements.
    - Score 2: Fair answer, addresses some aspects of the question but with significant errors.
    - Score 1: Poor answer, barely relevant to the question.
    - Score 0: Completely irrelevant or incorrect answer.

    Be somewhat lenient in scoring. Give credit for relevant points and deduct for incorrect or missing elements.
    Provide only the numeric score (0-5) without any explanation.
    """

    chat_session = model.start_chat(history=[])
    response = chat_session.send_message(prompt)
    
    try:
        score = float(response.text.strip())
        return max(0, min(5, score))  # Ensure score is between 0 and 5
    except ValueError:
        print(f"Error parsing score for question: {question}")
        return 0  # Default to 0 if parsing fails

# Evaluate all answers and create the report
evaluated_answers = []

for item in answers_data:
    question = item["question_text"]
    answer = item["answer"]
    score = evaluate_answer(question, answer)
    
    evaluated_answers.append({
        "question": question,
        "answer": answer,
        "score": score
    })

# Save the evaluated answers to report.json
with open('report.json', 'w') as report_file:
    json.dump(evaluated_answers, report_file, indent=2)

print("Report has been saved to report.json")

# Clear the contents of answers.json
with open('answers.json', 'w') as answers_file:
    json.dump([], answers_file)

print("Contents of answers.json have been cleared")
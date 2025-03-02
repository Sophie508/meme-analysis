import os
import json
import pandas as pd
from openai import OpenAI
import base64
from google.colab import drive
drive.mount('/content/drive')

# Set up API client for GPT
client = OpenAI(
    api_key="MY KEY",

)

test_file= "test.csv"
output_file = "GPT_results.json"

# 挂载 Google Drive
drive.mount('/content/drive')
# 设置 meme uploads 文件夹路径
meme_uploads_folder = "/content/drive/MyDrive/meme_uploads"
# Read test.csv
df = pd.read_csv(test_file)

# Store results
results = []

# Iterate through each row
total_images = len(df)
for index, row in df.iterrows():
    print(f"\nProcessing image {index + 1}/{total_images}: {row['Image_ID']}")

    image_id = row["Image_ID"]
    temp_path = os.path.join(meme_uploads_folder, image_id)  # Use the correct variable

    if not os.path.exists(temp_path):
        print(f"❌ Warning: Image {image_id} not found at {temp_path}. Skipping...") # Added path for debugging
        continue

    image_path = temp_path
    print("📸 Reading image file...")

    try:
        # Read image file and convert to base64
        with open(image_path, 'rb') as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')

        print("🤖 Sending request to GPT API...")
        # API request to GPT
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": [
                {"type": "text", "text": """For academic research purposes, please analyze this meme and provide the response in the following format:

Explanation: Provide a brief explanation of this meme related to US culture (20-30 words).

Misunderstanding: Describe a possible misunderstanding for non-US audiences (20-30 words).

Sentiment: [Choose one: Positive, Negative, or Neutral]

Emotions: [Choose one or more: Sarcastic, Humorous, Motivational, Offensive]"""},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
            ]}]
        )

        # Parse the response
        print("📝 Processing API response...")
        response_json = response.model_dump_json()
        parsed_response = json.loads(response_json)
        content = parsed_response.get("choices", [{}])[0].get("message", {}).get("content", "")

        # Extract sections using more robust parsing
        explanation = ""
        misunderstanding = ""
        sentiment = ""
        emotions = []

        # Parse each section
        sections = content.split("\n\n")
        for section in sections:
            if section.startswith("Explanation:"):
                explanation = section.replace("Explanation:", "").strip()
            elif section.startswith("Misunderstanding:"):
                misunderstanding = section.replace("Misunderstanding:", "").strip()
            elif section.startswith("Sentiment:"):
                sentiment = section.replace("Sentiment:", "").strip()
            elif section.startswith("Emotions:"):
                emotions_text = section.replace("Emotions:", "").strip()
                emotions = [e.strip() for e in emotions_text.strip("[]").split(",")]

        result = {
            "Image_ID": image_id,
            "Explanation": explanation,
            "Misunderstanding": misunderstanding,
            "Sentiment": sentiment,
            "Emotions": emotions
        }
        results.append(result)
        print("✅ Successfully processed image")
        print(f"📊 Output:\n{json.dumps(result, indent=2)}\n")
        print("-" * 80)

    except Exception as e:
        print(f"❌ Error processing {image_id}: {str(e)}")

# Save results to JSON file
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=4, ensure_ascii=False)

print(f"Results saved to {output_file}")

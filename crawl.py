import praw
import json
from datetime import datetime
import openai
import time
import requests
import base64
from io import BytesIO
from PIL import Image
import os
from typing import Dict, List, Optional
import webbrowser

reddit = praw.Reddit(
    client_id='ph2YerZ2hlDk26kz6fTPtw',
    client_secret='XqQwuuY-6yYFhj9im1lYhEF4sfBRSQ',
    user_agent='script:Sophie:v1.0 (by /u/Grouchy-Local8109)',
    read_only=True  
)
openai.api_key = "MY KEY" # openai api key here



def download_and_encode_image(url: str) -> Optional[str]:
    """Download image and encode it in base64."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # Handle GIFs by taking first frame and converting to PNG
        if url.lower().endswith(('.gif', '.gifv')):
            img = Image.open(BytesIO(response.content))
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            image_bytes = buffer.getvalue()
        else:
            # For non-GIF images, ensure they're in a supported format
            img = Image.open(BytesIO(response.content))
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            image_bytes = buffer.getvalue()

        return base64.b64encode(image_bytes).decode('utf-8')
    except Exception as e:
        print(f"Error downloading/processing image {url}: {e}")
        return None

def analyze_meme_context(post_data: Dict, image_url: str) -> Optional[Dict]:
    """Analyze meme context using GPT-4o."""
    try:
        # Prepare the conversation context
        thread_text = (
            f"Post Title: {post_data['title']}\n"
            f"Post Time: {post_data['created_utc']}\n"
            f"Post Content: {post_data['selftext']}\n\n"
            "Comments:\n"
        )

        for comment in post_data['comments']:
            thread_text += f"- {comment['body']}\n"

        # Encode the image
        base64_image = download_and_encode_image(image_url)
        if not base64_image:
            return None

        # Updated system message with stronger JSON formatting instructions
        system_message = """
        You are a meme context analyzer. Analyze the provided meme image and discussion context.
        You must respond with ONLY a raw JSON object (no markdown formatting, no ```json tags) in the following format:
        {
            "timestamp": "YYYY-MM-DD HH:MM:SS",
            "meme_topic": "Main subject or theme of the meme",
            "meme_explanation": "A detailed explanation of the meme, based on the context provided",
            "usage_context": "When and how this meme is typically used",
            "current_usage": "How the meme is being used in this specific post",
            "cultural_significance": "Any cultural or historical context",
            "emotional_tone": "The emotional impact or tone of the meme",
            "target_audience": "Who this meme appeals to",
            "virality_factors": "What makes this meme shareable or memorable",
            "meme_type": "The type of meme, determine from 4 types: 'Image Macros' (Memes with text overlay),
            'Visual Memes' (Memes without text rely solely on the image itself),
            'Text-based Memes' (Memes consist only of text without any associated image),
            'Hybrid Memes' (Memes combine both image and non-overlaid text, such as a picture with a separate caption posted above or below it.)",
            "additional_notes": "Any other relevant contextual information"
        }
        Do not include any markdown formatting, code blocks, or additional text.
        """

        messages = [
            {"role": "system", "content": system_message},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Analyze this meme and its context:\n{thread_text}"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ]

        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )

        # Get the response content and clean it
        response_content = response.choices[0].message.content.strip()

        # Clean markdown formatting if present
        if response_content.startswith('```'):
            # Remove the first line (```json)
            response_content = response_content.split('\n', 1)[1]
            # Remove the last line (```)
            response_content = response_content.rsplit('\n', 1)[0]

        # Add error checking and logging
        try:
            context_data = json.loads(response_content)
            return context_data
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print(f"Raw response: {response_content}")
            return None

    except Exception as e:
        print(f"Error analyzing meme context: {e}")
        return None

def process_memes_subreddit(limit: int = 50) -> List[Dict]:
    """Process posts from r/memes subreddit."""
    subreddit = reddit.subreddit('Funny')
    analyzed_posts = []
    processed_count = 0
    skipped_count = 0

    print(f"Starting to process {limit} posts from r/memes...")

    for submission in subreddit.hot(limit=limit):
        try:
            processed_count += 1

            # Skip posts without images or with few comments
            if not hasattr(submission, 'preview') or submission.num_comments < 5:
                skipped_count += 1
                print(f"[{processed_count}/{limit}] Skipped: No preview or few comments")
                continue

            # Get image URL
            image_url = submission.url

            # Skip unsupported URLs or non-image posts
            if not image_url.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.gifv', '.webp')):
                skipped_count += 1
                print(f"[{processed_count}/{limit}] Skipped: Unsupported image format")
                continue

            print(f"[{processed_count}/{limit}] Processing: {submission.title[:50]}...")
            # Collect comments
            submission.comments.replace_more(limit=5)
            comments = [
                {
                    'body': comment.body,
                    'score': comment.score,
                    'created_utc': datetime.fromtimestamp(comment.created_utc).isoformat()
                }
                for comment in submission.comments.list()[:20]  # Limit to top 20 comments
            ]

            # Prepare post data
            post_data = {
                'title': submission.title,
                'selftext': submission.selftext,
                'created_utc': datetime.fromtimestamp(submission.created_utc).isoformat(),
                'comments': comments
            }

            # Analyze meme context
            context_data = analyze_meme_context(post_data, image_url)

            if context_data:
                analyzed_posts.append({
                    'post_url': f"https://reddit.com{submission.permalink}",
                    'post_title': submission.title,
                    'image_url': image_url,
                    'context': context_data
                })
                print(f"✓ Successfully analyzed post {len(analyzed_posts)}")
            else:
                skipped_count += 1
                print("✗ Failed to analyze post")

            # Rate limiting
            time.sleep(2)

        except Exception as e:
            skipped_count += 1
            print(f"✗ Error processing submission: {e}")
            continue

    print(f"\nProcessing complete!")
    print(f"Total processed: {processed_count}")
    print(f"Successfully analyzed: {len(analyzed_posts)}")
    print(f"Skipped/Failed: {skipped_count}")

    return analyzed_posts

if __name__ == "__main__":
    # Process memes
    results = process_memes_subreddit(limit=1000)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"meme_analysis_{timestamp}.json"

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Analyzed {len(results)} meme posts")
    print(f"Results saved to {filename}")

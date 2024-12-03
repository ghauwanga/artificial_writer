import random
import nltk
from nltk import ngrams

# Ensure you have the necessary NLTK resources
nltk.download('punkt')


class TextProcessor:
    """Class to process and generate new text from fetched text."""

    def __init__(self, text):
        self.text = text
        self.words = nltk.word_tokenize(self.text)  # Tokenize the text into words
        self.ngrams = list(ngrams(self.words, 3))  # Create trigrams for better context

    def generate_text(self, num_sentences=5, fragment_length=5):
        """Generate new text by extracting and combining fragments."""
        new_text = []
        for _ in range(num_sentences):
            # Randomly select a starting point for the fragment
            start_index = random.randint(0, len(self.words) - fragment_length)
            fragment = ' '.join(self.words[start_index:start_index + fragment_length])
            new_text.append(fragment.capitalize() + '.')  # Capitalize and add a period

        # Join the sentences into a coherent paragraph
        return ' '.join(new_text)

    def generate_logical_text(self, total_length=100):
        """Generate a longer, more logical text."""
        new_text = []
        current_length = 0

        while current_length < total_length:
            # Randomly select a starting point for the fragment
            start_index = random.randint(0, len(self.words) - 1)
            fragment = self.words[start_index]

            # Add more words to the fragment until reaching the desired length
            while current_length < total_length and start_index < len(self.words):
                new_text.append(fragment)
                current_length += len(fragment) + 1  # +1 for the space
                start_index += 1
                if start_index < len(self.words):
                    fragment = self.words[start_index]

        # Join the words into a coherent paragraph
        return ' '.join(new_text).capitalize() + '.'


# Example usage
# if __name__ == "__main__":
#     sample_text = "This is a sample text that will be used to demonstrate the text generation capabilities of the TextProcessor class. The goal is to create coherent and logical sentences from the provided text."
#     processor = TextProcessor(sample_text)
#
#     # Generate logical text
#     generated_text = processor.generate_logical_text(total_length=200)
#     print(generated_text)

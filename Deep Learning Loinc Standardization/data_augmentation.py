import numpy as np
import random
import string
import re

# Set seed for reproducibility
random.seed(42)
np.random.seed(42)

def random_deletion(text, p=0.1):
    """
    Randomly delete characters from the text with probability p
    
    Args:
        text (str): Input text
        p (float): Probability of deleting each character
        
    Returns:
        str: Text with some characters randomly deleted
    """
    if not text or p <= 0:
        return text
        
    chars = list(text)
    chars = [c for c in chars if random.random() > p]
    
    if not chars:  # Ensure at least one character remains
        return text[0]
        
    return ''.join(chars)


def random_swap(text, n=1):
    """
    Randomly swap n pairs of words in the text
    
    Args:
        text (str): Input text
        n (int): Number of swaps to perform
        
    Returns:
        str: Text with words swapped
    """
    if not text:
        return text
        
    words = text.split()
    if len(words) < 2:
        return text
        
    for _ in range(n):
        if len(words) >= 2:  # Need at least 2 words to swap
            idx1, idx2 = random.sample(range(len(words)), 2)
            words[idx1], words[idx2] = words[idx2], words[idx1]
            
    return ' '.join(words)


def random_insertion(text, related_terms=None, n=1):
    """
    Randomly insert words from related_terms into the text n times
    
    Args:
        text (str): Input text
        related_terms (str): Semicolon-separated related terms to choose from
        n (int): Number of insertions to perform
        
    Returns:
        str: Text with inserted words
    """
    if not text:
        return text
        
    words = text.split()
    
    # If no related terms provided, duplicate a random word from the text
    if not related_terms or related_terms == '':
        if not words:
            return text
        related_words = words
    else:
        # Split related terms by semicolon and remove any empty strings
        related_words = [w.strip() for w in related_terms.split(';') if w.strip()]
        if not related_words:
            related_words = words if words else [text]
            
    for _ in range(n):
        if related_words:
            # Choose a random word from related terms
            new_word = random.choice(related_words)
            
            # Choose a random position to insert
            insert_pos = random.randint(0, len(words))
            words.insert(insert_pos, new_word)
            
    return ' '.join(words)


def acronym_substitution(text, related_terms=None):
    """
    Substitute words or phrases with their acronyms or vice versa
    
    Args:
        text (str): Input text
        related_terms (str): Semicolon-separated related terms that might include acronyms
        
    Returns:
        str: Text with some substitutions
    """
    if not text or not related_terms:
        return text
        
    # Common medical acronym substitutions based on the examples in the paper
    acronyms = {
        'cerebrospinal fluid': 'csf',
        'blood': 'bld',
        'serum': 'ser',
        'serum or plasma': 'serpl',
        'plasma': 'plas',
        'presence': 'ql',
        'qualitative': 'qual',
        'point in time': 'pt',
        'tricyclic antidepressants': 'tcas'
    }
    
    # Add additional acronyms from related terms if they look like acronyms
    # For example, if a term is in all caps or has a specific pattern
    if related_terms:
        terms = [term.strip() for term in related_terms.split(';')]
        for term in terms:
            # If term is all caps and length <= 5, consider it as a potential acronym
            if term.isupper() and len(term) <= 5:
                # Look for matching phrases in text that could be expanded to this acronym
                # This is a simplified approach; in a real system, this would be more sophisticated
                pass
                
    # Pick a random substitution to apply
    result = text
    for phrase, acronym in acronyms.items():
        if phrase in text.lower():
            # 50% chance to replace phrase with acronym
            if random.random() > 0.5:
                result = re.sub(r'\b' + re.escape(phrase) + r'\b', acronym, result, flags=re.IGNORECASE)
                break
        elif acronym in text.lower():
            # 50% chance to replace acronym with phrase
            if random.random() > 0.5:
                result = re.sub(r'\b' + re.escape(acronym) + r'\b', phrase, result, flags=re.IGNORECASE)
                break
                
    return result


def append_scale_token(text, scale_type=None):
    """
    Append a scale sentinel token to the text.
    
    Args:
        text (str): Input text
        scale_type (str): The SCALE_TYP value (e.g., 'Qn', 'Ql', 'Ord', etc.)
        
    Returns:
        str: Text with the scale sentinel token appended
    """
    if not text:
        return text
    
    # If scale type is not provided or empty, use 'unk' as the default
    if not scale_type or scale_type.strip() == '':
        scale_type = 'unk'
    
    # Convert scale type to lowercase for consistency
    scale_type = scale_type.lower()
    
    # Append the sentinel token to the text
    return f"{text} ##scale={scale_type}##"


def augment_text(text, related_terms=None, num_augmentations=5, scale_type=None):
    """
    Apply various text augmentation techniques to generate multiple variants of the input text
    
    Args:
        text (str): Input text
        related_terms (str): Semicolon-separated related terms
        num_augmentations (int): Number of augmented examples to generate
        scale_type (str): The SCALE_TYP value for the sentinel token
        
    Returns:
        list: List of augmented text strings
    """
    if not text:
        return []
        
    # Apply scale token to original text if scale_type is provided
    if scale_type:
        text = append_scale_token(text, scale_type)
        
    augmented_texts = [text]  # Include original text
    
    for _ in range(num_augmentations - 1):  # -1 because we already included the original
        # Choose a random sequence of augmentations to apply
        augmentation_pipeline = []
        
        # 50% chance to include each augmentation technique
        if random.random() > 0.5:
            augmentation_pipeline.append(lambda t: random_deletion(t, p=0.1))
            
        if random.random() > 0.5:
            augmentation_pipeline.append(lambda t: random_swap(t, n=1))
            
        if random.random() > 0.5 and related_terms:
            augmentation_pipeline.append(lambda t: random_insertion(t, related_terms, n=1))
            
        if random.random() > 0.5 and related_terms:
            augmentation_pipeline.append(lambda t: acronym_substitution(t, related_terms))
            
        # If no augmentations were selected, add at least one
        if not augmentation_pipeline:
            augmentation_pipeline.append(lambda t: random_swap(t, n=1))
            
        # Apply the selected augmentations
        # Start with the original text without scale token to avoid augmenting the token itself
        if scale_type:
            augmented_text = text.split(" ##scale=")[0]
        else:
            augmented_text = text
            
        for augmentation_func in augmentation_pipeline:
            augmented_text = augmentation_func(augmented_text)
            
        # Add scale token after augmentations if scale_type is provided
        if scale_type:
            augmented_text = append_scale_token(augmented_text, scale_type)
            
        augmented_texts.append(augmented_text)
        
    return augmented_texts


# Example usage
if __name__ == "__main__":
    # Example from the paper
    source_text = "tricyclic antidepressant screen blood"
    related_terms = "tricyclics; tcas; antidepressants; serum or plasma; [presence]; ql"
    
    augmented_examples = augment_text(source_text, related_terms, num_augmentations=10)
    
    print("Original text:", source_text)
    print("\nAugmented examples:")
    for i, example in enumerate(augmented_examples, 1):
        print(f"{i}. {example}")
    
    # Example with LOINC text
    loinc_text = "Tricyclic antidepressants [Presence] in Serum or Plasma"
    loinc_related = "Tricyclics SerPl Ql; Tricyclic antidepressants Ql; tcas; screen; blood"
    
    loinc_augmented = augment_text(loinc_text, loinc_related, num_augmentations=10)
    
    print("\nOriginal LOINC text:", loinc_text)
    print("\nAugmented LOINC examples:")
    for i, example in enumerate(loinc_augmented, 1):
        print(f"{i}. {example}") 
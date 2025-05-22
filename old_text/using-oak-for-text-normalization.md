# Using OAK in Python Code: A Guide for LLMs

## 1. Basic OAK Setup and Initialization

```python
from oaklib import get_adapter

# Initialize an OAK adapter for a specific ontology
# Format: "sqlite:obo:<ontology_name>"
envo_adapter = get_adapter("sqlite:obo:envo")
po_adapter = get_adapter("sqlite:obo:po")
# etc.
```

## 2. Core OAK Operations

### Getting Labels from CURIEs

```python
# Simple label lookup
label = adapter.label('ENVO:01000813')  # Returns the rdfs:label for the CURIE

# Check if term is obsolete
is_obsolete = adapter.is_obsolete('ENVO:01000813')
```

### Text Annotation with OAK

```python
from oaklib.datamodels.text_annotator import TextAnnotationConfiguration

# Configure annotation settings
config = TextAnnotationConfiguration()
config.match_whole_words_only = True  # Prevent partial word matches

# Annotate text
annotations = adapter.annotate_text('your text here', configuration=config)

# Process annotations
for annotation in annotations:
    print(f"Match: {annotation.match_string}")
    print(f"CURIE: {annotation.object_id}")
    print(f"Label: {annotation.object_label}")
    print(f"Position: {annotation.subject_start}-{annotation.subject_end}")
```

## 3. Working with Lexical Indexes

### Loading/Creating Lexical Indexes

```python
from oaklib.utilities.lexical.lexical_indexer import (
    load_lexical_index,
    create_lexical_index,
    save_lexical_index
)

# Try loading existing index
LEX_INDEX_FILE = "expanded_envo_po_lexical_index.yaml"

try:
    lexical_index = load_lexical_index(LEX_INDEX_FILE)
except FileNotFoundError:
    # Create new index if file doesn't exist
    adapter = get_adapter("sqlite:obo:envo")
    lexical_index = create_lexical_index(adapter)
    # Save for future use
    save_lexical_index(lexical_index, LEX_INDEX_FILE)
```

### Creating Element-to-Label Maps

```python
def build_element_to_label_map(lexical_index):
    """Extract CURIE to label mapping from lexical index."""
    index_data = lexical_index._as_dict
    element_to_label = {}
    
    for term, grouping in index_data["groupings"].items():
        for rel in grouping["relationships"]:
            if rel["predicate"] == "rdfs:label":
                element = rel["element"]
                label = rel["element_term"]
                element_to_label[element] = label
                
    return element_to_label
```

## 4. Text Annotation Best Practices

### Filtering and Processing Annotations

```python
def filter_annotations(annotations, min_length=3):
    """Filter annotations based on quality criteria."""
    filtered = []
    for ann in annotations:
        # Skip too-short annotations
        if hasattr(ann, "subject_start") and hasattr(ann, "subject_end"):
            ann_length = ann.subject_end - ann.subject_start + 1
            if ann_length < min_length:
                continue
                
        # Ensure whole word matches for single words
        match_string = getattr(ann, "match_string", None)
        if match_string and " " not in match_string:
            if not is_true_whole_word_match(label, match_string):
                continue
                
        filtered.append(ann)
    return filtered

def is_true_whole_word_match(text, match_string):
    """Verify if match_string occurs as a complete word."""
    words = re.findall(r"\b\w+\b", text.lower())
    return match_string.lower() in words
```

### Computing Annotation Coverage

```python
def compute_annotation_coverage(annotations, text_length):
    """Calculate what percentage of text is covered by annotations."""
    intervals = []
    for ann in annotations:
        if hasattr(ann, "subject_start") and hasattr(ann, "subject_end"):
            intervals.append((ann.subject_start, ann.subject_end))
            
    if not intervals or text_length == 0:
        return 0
        
    # Merge overlapping intervals
    intervals.sort(key=lambda x: x[0])
    merged = []
    current_start, current_end = intervals[0]
    
    for start, end in intervals[1:]:
        if start <= current_end + 1:  # Adjacent or overlapping
            current_end = max(current_end, end)
        else:
            merged.append((current_start, current_end))
            current_start, current_end = start, end
            
    merged.append((current_start, current_end))
    
    total_covered = sum(end - start + 1 for start, end in merged)
    return total_covered / text_length
```

## 5. Supported Ontologies

The code shows support for many ontologies via SQLite backends. Here's a partial list:

```python
SUPPORTED_ONTOLOGIES = {
    "agro": "sqlite:obo:agro",
    "bco": "sqlite:obo:bco", 
    "chebi": "sqlite:obo:chebi",
    "envo": "sqlite:obo:envo",
    "po": "sqlite:obo:po",
    "uberon": "sqlite:obo:uberon",
    # Many more available
}
```

## 6. Error Handling and Best Practices

```python
def safe_oak_operation(curie, adapter):
    """Safely perform OAK operations with error handling."""
    try:
        label = adapter.label(curie)
        if label:
            try:
                obsolete = adapter.is_obsolete(curie)
            except Exception:
                obsolete = False
            return {
                "curie": curie,
                "label": label,
                "obsolete": obsolete
            }
    except Exception as e:
        print(f"Error processing {curie}: {str(e)}")
    return None
```

## Notes for LLMs

1. Always normalize CURIEs to use uppercase prefixes (e.g., 'ENVO:' not 'envo:')
2. Cache lexical indexes when possible to improve performance
3. Use whole word matching to avoid false positives in text annotation
4. Consider text length and annotation coverage when evaluating results
5. Handle obsolete terms appropriately in your application context
6. Be aware that some operations may require web API access (e.g., BioPortal)

The repository demonstrates these approaches being used for environmental context annotation, but the same patterns can be applied to any domain using OAK-supported ontologies.

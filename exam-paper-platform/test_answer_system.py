#!/usr/bin/env python3
"""
Quick test to verify the answer generation system is properly set up.

Run this to validate:
1. All imports work
2. Environment variables are set
3. Vector store is accessible
4. LLM is accessible
"""

import sys
from pathlib import Path

# Add parent directory
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test all required imports."""
    print("Testing imports...")
    try:
        from app.rag.embeddings import embed_texts
        print("  ✓ embeddings module")
        
        from app.rag.vector_store import PineconeVectorStore
        print("  ✓ vector_store module")
        
        from groq import Groq
        print("  ✓ groq module")
        
        from scripts.generate_answers import generate_answer
        print("  ✓ generate_answers module")
        
        return True
    except ImportError as e:
        print(f"  ✗ Import error: {e}")
        return False

def test_environment():
    """Test environment variables."""
    print("\nTesting environment variables...")
    import os
    
    required = ["GROQ_API_KEY", "PINECONE_API_KEY"]
    all_set = True
    
    for var in required:
        if os.getenv(var):
            print(f"  ✓ {var} is set")
        else:
            print(f"  ✗ {var} is NOT set")
            all_set = False
    
    return all_set

def test_pinecone():
    """Test Pinecone connectivity."""
    print("\nTesting Pinecone...")
    try:
        from app.rag.vector_store import PineconeVectorStore
        
        store = PineconeVectorStore()
        print(f"  ✓ Connected to Pinecone")
        print(f"    - Index: {store.index_name}")
        print(f"    - Dimension: {store.dimension}")
        print(f"    - Metric: {store.metric}")
        return True
    except Exception as e:
        print(f"  ✗ Pinecone error: {e}")
        return False

def test_groq():
    """Test Groq connectivity."""
    print("\nTesting Groq...")
    try:
        from groq import Groq
        import os
        
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        models = client.models.list()
        print(f"  ✓ Connected to Groq")
        print(f"    - Available models: {len(models.data)}")
        
        # Check for our specific model
        model_names = [m.id for m in models.data]
        if "mixtral-8x7b-32768" in model_names:
            print(f"    - mixtral-8x7b-32768: ✓")
        else:
            print(f"    - mixtral-8x7b-32768: ✗ (not available)")
        
        return True
    except Exception as e:
        print(f"  ✗ Groq error: {e}")
        return False

def test_embeddings():
    """Test embedding generation."""
    print("\nTesting embeddings...")
    try:
        from app.rag.embeddings import embed_texts
        
        test_text = "What is the power factor?"
        embeddings = embed_texts([test_text])
        
        if embeddings and len(embeddings) > 0:
            print(f"  ✓ Embeddings generated")
            print(f"    - Dimension: {len(embeddings[0])}")
            return True
        else:
            print(f"  ✗ No embeddings generated")
            return False
    except Exception as e:
        print(f"  ✗ Embedding error: {e}")
        return False

def test_answer_generation():
    """Test answer generation (sample)."""
    print("\nTesting answer generation...")
    try:
        from scripts.generate_answers import generate_answer
        
        print("  ⏳ Generating sample answer (may take 10-15 seconds)...")
        
        result = generate_answer(
            question="What is the impedance of a circuit with R=10Ω and XL=5Ω?",
            concept="AC Circuits",
            difficulty="Easy",
            namespace="Electrical Engineering"
        )
        
        if result and result.get("answer"):
            print(f"  ✓ Answer generated successfully")
            print(f"    - Length: {len(result['answer'])} chars")
            print(f"    - Context retrieved: {result.get('context_retrieved', False)}")
            print(f"    - Sample: {result['answer'][:100]}...")
            return True
        else:
            print(f"  ✗ No answer generated")
            return False
    except Exception as e:
        print(f"  ✗ Answer generation error: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 70)
    print("ANSWER GENERATION SYSTEM - VALIDATION TEST")
    print("=" * 70)
    
    results = {
        "Imports": test_imports(),
        "Environment": test_environment(),
        "Pinecone": test_pinecone(),
        "Groq": test_groq(),
        "Embeddings": test_embeddings(),
    }
    
    # Only test answer generation if everything else passes
    if all(results.values()):
        results["Answer Generation"] = test_answer_generation()
    else:
        print("\n⚠️  Skipping answer generation test (dependencies not ready)")
        results["Answer Generation"] = False
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:.<50} {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✓ ALL TESTS PASSED - System is ready!")
        print("\nNext steps:")
        print("  1. Run: python scripts/generate_answers.py --sample 3")
        print("  2. Check: answers.json")
        print("  3. Try full workflow: python scripts/generate_exam_with_answers.py generate --total 5")
        return 0
    else:
        print("✗ SOME TESTS FAILED - Please review the errors above")
        print("\nFix issues:")
        print("  1. Check .env file has GROQ_API_KEY and PINECONE_API_KEY")
        print("  2. Verify Pinecone index exists and has data")
        print("  3. Run 'pip install -r requirements.txt' to install dependencies")
        print("  4. Re-run this test to verify fixes")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(130)

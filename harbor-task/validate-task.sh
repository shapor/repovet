#!/bin/bash
# Validation script for Harbor task structure

set -e

TASK_DIR="repovet-trust-assessment"
echo "=== Validating Harbor Task: $TASK_DIR ==="
echo

# Check required files
echo "Checking required files..."
required_files=(
  "$TASK_DIR/task.toml"
  "$TASK_DIR/instruction.md"
  "$TASK_DIR/environment/Dockerfile"
  "$TASK_DIR/tests/test.sh"
  "$TASK_DIR/solution/solve.sh"
)

for file in "${required_files[@]}"; do
  if [ -f "$file" ]; then
    echo "  ✅ $file"
  else
    echo "  ❌ $file MISSING"
    exit 1
  fi
done

echo
echo "Checking file permissions..."
if [ -x "$TASK_DIR/tests/test.sh" ]; then
  echo "  ✅ tests/test.sh is executable"
else
  echo "  ❌ tests/test.sh is not executable"
  exit 1
fi

if [ -x "$TASK_DIR/solution/solve.sh" ]; then
  echo "  ✅ solution/solve.sh is executable"
else
  echo "  ❌ solution/solve.sh is not executable"
  exit 1
fi

echo
echo "Checking task.toml structure..."
if grep -q "version = \"1.0\"" "$TASK_DIR/task.toml"; then
  echo "  ✅ Version specified"
else
  echo "  ❌ Version missing"
  exit 1
fi

if grep -q "\[metadata\]" "$TASK_DIR/task.toml"; then
  echo "  ✅ Metadata section present"
else
  echo "  ❌ Metadata section missing"
  exit 1
fi

if grep -q "\[verifier\]" "$TASK_DIR/task.toml"; then
  echo "  ✅ Verifier section present"
else
  echo "  ❌ Verifier section missing"
  exit 1
fi

if grep -q "\[agent\]" "$TASK_DIR/task.toml"; then
  echo "  ✅ Agent section present"
else
  echo "  ❌ Agent section missing"
  exit 1
fi

if grep -q "\[environment\]" "$TASK_DIR/task.toml"; then
  echo "  ✅ Environment section present"
else
  echo "  ❌ Environment section missing"
  exit 1
fi

echo
echo "Checking Dockerfile..."
if grep -q "FROM ubuntu" "$TASK_DIR/environment/Dockerfile"; then
  echo "  ✅ Base image specified"
else
  echo "  ⚠️  Non-standard base image"
fi

if grep -q "gh" "$TASK_DIR/environment/Dockerfile"; then
  echo "  ✅ GitHub CLI (gh) installed"
else
  echo "  ⚠️  GitHub CLI not found in Dockerfile"
fi

echo
echo "Checking test files..."
if [ -f "$TASK_DIR/tests/test_assessment.py" ]; then
  echo "  ✅ test_assessment.py present"

  # Check for pytest tests
  if grep -q "def test_" "$TASK_DIR/tests/test_assessment.py"; then
    echo "  ✅ Pytest test functions found"
  else
    echo "  ❌ No pytest test functions"
    exit 1
  fi
else
  echo "  ❌ test_assessment.py missing"
  exit 1
fi

echo
echo "=== ✅ All validation checks passed! ==="
echo
echo "Task structure is valid and ready for Harbor integration."
echo
echo "Next steps:"
echo "  1. Test locally: docker build -t repovet-task $TASK_DIR/environment"
echo "  2. Run solution: docker run --rm -v \$(pwd)/$TASK_DIR/solution:/solution repovet-task bash /solution/solve.sh"
echo "  3. Run with Harbor: harbor run --task ./$TASK_DIR --agent claude-code --model anthropic/claude-opus-4-6"

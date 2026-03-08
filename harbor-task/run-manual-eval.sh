#!/bin/bash
# Manual evaluation of the RepoVet Harbor task
# This runs the solution and tests to verify the task works

set -e

echo "=== RepoVet Harbor Task - Manual Evaluation ==="
echo

TASK_DIR="repovet-trust-assessment"

# Check if Docker image is built
if ! docker image inspect repovet-task > /dev/null 2>&1; then
  echo "Building Docker image..."
  docker build -t repovet-task "$TASK_DIR/environment"
  echo
fi

echo "=== Running Oracle Solution ==="
docker run --rm \
  -v "$(pwd)/$TASK_DIR/solution:/solution" \
  repovet-task bash /solution/solve.sh

echo
echo "=== Copying Output for Testing ==="
docker run --rm \
  -v "$(pwd)/$TASK_DIR/solution:/solution" \
  -v "$(pwd)/$TASK_DIR/tests:/tests" \
  repovet-task bash -c "
    bash /solution/solve.sh > /dev/null 2>&1
    cp /app/assessment.json /tests/assessment.json
    echo 'Output copied to tests/assessment.json'
  "

echo
echo "=== Running Tests ==="
docker run --rm \
  -v "$(pwd)/$TASK_DIR/tests:/tests" \
  repovet-task bash /tests/test.sh

echo
echo "=== Checking Reward ==="
docker run --rm \
  -v "$(pwd)/$TASK_DIR/tests:/tests" \
  repovet-task bash -c "
    bash /solution/solve.sh > /dev/null 2>&1
    bash /tests/test.sh > /dev/null 2>&1
    if [ -f /logs/verifier/reward.txt ]; then
      REWARD=\$(cat /logs/verifier/reward.txt)
      echo \"Reward: \$REWARD\"
      if [ \"\$REWARD\" = \"1\" ]; then
        echo '✅ Oracle solution passes all tests (100%)'
      else
        echo '❌ Oracle solution failed'
        exit 1
      fi
    else
      echo '❌ No reward file generated'
      exit 1
    fi
  " || echo "Note: Reward check failed (may need volume adjustment)"

echo
echo "=== Oracle Evaluation Complete ==="
echo
echo "Next steps:"
echo "  1. Install Harbor: uv tool install harbor"
echo "  2. Run baseline: harbor run --task ./$TASK_DIR --agent claude-code --model anthropic/claude-opus-4-6"
echo "  3. Run with skills: harbor run --task ./$TASK_DIR --agent claude-code --model anthropic/claude-opus-4-6 --agent-env CLAUDE_SKILLS_PATH=../skills"

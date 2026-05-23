#!/bin/bash
COMMIT_MSG="${1:-Auto update}"
/usr/bin/git add .
/usr/bin/git commit -m "$COMMIT_MSG"
/usr/bin/git push

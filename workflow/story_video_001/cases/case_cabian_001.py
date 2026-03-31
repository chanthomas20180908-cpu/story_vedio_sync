from __future__ import annotations

from workflow.story_video_001.activities.activity_script_001 import main
from workflow.story_video_001.profiles.profile_cabian_001 import PROFILE

'''
PYTHONPATH=/Users/test/code/Python/AI_vedio_demo/pythonProject \
/Users/test/code/Python/AI_vedio_demo/pythonProject/.venv/bin/python3 \
  -m workflow.story_video_001.cases.case_cabian_001 \
  --input '/Users/test/Library/Mobile Documents/com~apple~CloudDocs/BEAST_BEING/my_mutimedia/my_scripts/rpt口播视频/05_merged_segments_fixed_20260212_143836/0036_第二十回_seg006_赛昆仑报丧.md'
'''

if __name__ == "__main__":
    raise SystemExit(main(profile=PROFILE))

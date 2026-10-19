# Third fictional jury member

Created with the built-in imagegen tool on 2026-10-15. Source asset:
frontend/public/avatars/daniel-fictional-source.png.

Prompt: photorealistic studio portrait of a completely fictional male Bolivian /
Andean Latin American university professor, about 52, medium tan complexion,
short salt-and-pepper hair, thin rectangular dark glasses, clean shaven, attentive
neutral expression, gently closed lips, open eyes looking at the camera. Charcoal
suit, white collared shirt, muted burgundy tie, hands together at waist level.
Frontal waist-up framing with head and shoulders visible, natural skin texture,
soft even lighting, flat chroma green #00ff00 background, 3:4 portrait. No text,
logos or resemblance to a known person.

The still portrait is encoded into a short source video, then processed by
the official DH_live CPU preparation pipeline with its publicly supplied
SCRFD, FaceLandmarker and DINet_mini checkpoints. This creates a mouth that can
be driven by speech. It does not generate new body gestures or natural blinking
from the still photograph. The source image is retained intact.

Preparation command (explicit local paths):

```
python infrastructure/scripts/prepare_jury_avatar.py --source frontend/public/avatars/daniel-fictional-source.png --engine-root PATH_TO_DH_LIVE --output frontend/public/vendor/dh-live/daniel-fictional
```

The tool checks the absolute intermediate directory before invoking upstream
code that removes its disposable extracted frames. DH_live attribution and mark
remain in place. Other two characters are still upstream demonstration assets.

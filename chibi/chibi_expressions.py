"""Her expressions (face only), from her expressions sheet and the faces in her ChatGPT pose sheets.

    head_svg_v2(**expression("angry"), pose=...)

eyes: open | half | closed | happy (per eye for a wink); look: iris offset (y about -4 = eye-roll);
brows: (lift, angle): angle > 0 = inner ends down (angry), < 0 = inner ends up (sad / worried);
mouth: smile | open | wide | oh | frown.
"""
EXPRESSIONS = {
    "neutral":   dict(eyes="open", look=(0, 0), brows=(0, 0), mouth_shape="smile"),
    "happy":     dict(eyes="happy", look=(0, 0), brows=(3, -4), mouth_shape="open"),
    "calm":      dict(eyes="closed", look=(0, 0), brows=(1, -2), mouth_shape="smile"),
    "smug":      dict(eyes="half", look=(0, 0.3), brows=((4, 4), (-1, 6)), mouth_shape="smile"),
    "wink":      dict(eyes=("open", "happy"), look=(0, 0), brows=((2, -2), (-1, 4)), mouth_shape="open"),
    "angry":     dict(eyes="open", look=(0, 0.4), brows=(-4, 14), mouth_shape="frown"),
    "annoyed":   dict(eyes="half", look=(0, 0.4), brows=(-2, 9), mouth_shape="frown"),
    "eye_roll":  dict(eyes="open", look=(0.6, -4.2), brows=(3, -3), mouth_shape="frown"),
    "surprised": dict(eyes="open", look=(0, 0), brows=(9, -3), mouth_shape="oh"),
    "sad":       dict(eyes="open", look=(0, 0.8), brows=(2, -20), mouth_shape="frown"),
    "excited":   dict(eyes="open", look=(0, 0), brows=(6, -3), mouth_shape="wide"),
}


def expression(name):
    return dict(EXPRESSIONS[name])

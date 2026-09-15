from PIL import Image, ImageOps, ImageDraw, ImageFont
import os


#===== BASE DIRECTORY =====

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)


#===== ASSETS =====

ASSETS_FOLDER = os.path.join(
    BASE_DIR,
    "assets"
)

ASSETS_IMAGE_FOLDER = os.path.join(
    ASSETS_FOLDER,
    "images"
)

FONTS_FOLDER = os.path.join(
    ASSETS_FOLDER,
    "fonts"
)


#===== DATA =====

DATA_FOLDER = os.path.join(
    BASE_DIR,
    "data"
)


#===== FILES =====

BLANK_IMAGE = os.path.join(
    ASSETS_IMAGE_FOLDER,
    "blank_auction.jpg"
)

NAME_FONT = os.path.join(
    FONTS_FOLDER,
    "American Brewery Rough.ttf"
)

NATIONALITY_FONT = os.path.join(
    FONTS_FOLDER,
    "Super Jello.ttf"
)

PRICE_FONT = os.path.join(
    FONTS_FOLDER,
    "valve bd.otf"
)


#===== IMAGE SIZE =====

TARGET_SIZE = (
    1600,
    900
)


#===== FONT LOADER =====

def load_font(
    font_path,
    size
):

    try:

        if os.path.exists(
            font_path
        ):

            return ImageFont.truetype(
                font_path,
                size
            )

    except Exception as e:

        print(
            "FONT ERROR:",
            repr(e)
        )

    return ImageFont.load_default()


#===== DYNAMIC PLACEHOLDER =====

def create_placeholder(
    player_name,
    country,
    base_price
):

    if not os.path.exists(
        BLANK_IMAGE
    ):

        print(
            "WARNING: blank_auction.jpg not found:",
            BLANK_IMAGE
        )

        return None

    image = Image.open(
        BLANK_IMAGE
    ).convert("RGB")

    image = ImageOps.fit(
        image,
        TARGET_SIZE,
        method=Image.Resampling.LANCZOS,
        centering=(
            0.5,
            0.5
        )
    )

    draw = ImageDraw.Draw(
        image
    )


    #===== PLAYER NAME =====

    draw.rectangle(
        (
            180,
            80,
            1420,
            280
        ),
        fill="white"
    )

    image_player_name = str(
        player_name
    ).upper()

    name_size = 160

    while name_size >= 35:

        name_font = load_font(
            NAME_FONT,
            name_size
        )

        bbox = draw.textbbox(
            (
                0,
                0
            ),
            image_player_name,
            font=name_font
        )

        width = (
            bbox[2]
            - bbox[0]
        )

        if width <= 1150:

            break

        name_size -= 5

    bbox = draw.textbbox(
        (
            0,
            0
        ),
        image_player_name,
        font=name_font
    )

    width = (
        bbox[2]
        - bbox[0]
    )

    x = (
        TARGET_SIZE[0]
        - width
    ) // 2

    draw.text(
        (
            x,
            115
        ),
        image_player_name,
        font=name_font,
        fill=(
            55,
            35,
            220
        )
    )


    #===== NATIONALITY =====

    flag = {
        "India": "🇮🇳",
        "Australia": "🇦🇺",
        "England": "🏴",
        "South Africa": "🇿🇦",
        "New Zealand": "🇳🇿",
        "Sri Lanka": "🇱🇰",
        "Bangladesh": "🇧🇩",
        "Afghanistan": "🇦🇫",
        "Pakistan": "🇵🇰",
        "West Indies": "🌴",
        "Zimbabwe": "🇿🇼",
        "Ireland": "🇮🇪",
        "Nepal": "🇳🇵",
        "United States": "🇺🇸"
    }.get(
        country,
        "🌎"
    )

    draw.rectangle(
        (
            200,
            300,
            1400,
            500
        ),
        fill="white"
    )

    nationality_font = load_font(
        NATIONALITY_FONT,
        130
    )

    flag_font = ImageFont.load_default()

    country_bbox = draw.textbbox(
        (
            0,
            0
        ),
        country,
        font=nationality_font
    )

    country_width = (
        country_bbox[2]
        - country_bbox[0]
    )

    flag_bbox = draw.textbbox(
        (
            0,
            0
        ),
        flag,
        font=flag_font
    )

    flag_width = (
        flag_bbox[2]
        - flag_bbox[0]
    )

    gap = 25

    total_width = (
        country_width
        + gap
        + flag_width
    )

    x = (
        TARGET_SIZE[0]
        - total_width
    ) // 2

    draw.text(
        (
            x,
            340
        ),
        country,
        font=nationality_font,
        fill="black"
    )

    draw.text(
        (
            x
            + country_width
            + gap,
            340
        ),
        flag,
        font=flag_font,
        fill="black"
    )


    #===== BASE PRICE =====

    price_text = (
        f"₹{float(base_price):.2f} Cr"
    )

    draw.rectangle(
        (
            200,
            520,
            1400,
            750
        ),
        fill="white"
    )

    price_font = load_font(
        PRICE_FONT,
        140
    )

    bbox = draw.textbbox(
        (
            0,
            0
        ),
        price_text,
        font=price_font
    )

    width = (
        bbox[2]
        - bbox[0]
    )

    x = (
        TARGET_SIZE[0]
        - width
    ) // 2

    draw.text(
        (
            x,
            570
        ),
        price_text,
        font=price_font,
        fill=(
            220,
            30,
            30
        )
    )


    #===== SAVE PLACEHOLDER =====

    output_path = os.path.join(
        DATA_FOLDER,
        "temp_auction_placeholder.jpg"
    )

    os.makedirs(
        DATA_FOLDER,
        exist_ok=True
    )

    image.save(
        output_path,
        "JPEG",
        quality=95
    )

    return output_path


#===== PREPARE PLAYER IMAGE =====

def prepare_player_image(
    image_name,
    player_name,
    country,
    base_price
):

    output_path = os.path.join(
        DATA_FOLDER,
        "temp_auction_image.jpg"
    )

    try:

        #===== REAL PLAYER IMAGE =====

        if image_name:

            image_name = str(
                image_name
            ).strip()

            image_path = os.path.join(
                ASSETS_IMAGE_FOLDER,
                image_name
            )

            print(
                "PLAYER IMAGE CHECK:",
                image_path
            )

            if os.path.exists(
                image_path
            ):

                image = Image.open(
                    image_path
                ).convert("RGB")

                image = ImageOps.fit(
                    image,
                    TARGET_SIZE,
                    method=Image.Resampling.LANCZOS,
                    centering=(
                        0.5,
                        0.5
                    )
                )

                os.makedirs(
                    DATA_FOLDER,
                    exist_ok=True
                )

                image.save(
                    output_path,
                    "JPEG",
                    quality=95
                )

                print(
                    "PLAYER IMAGE FOUND:",
                    image_path
                )

                return output_path

            print(
                "PLAYER IMAGE NOT FOUND:",
                image_path
            )


        #===== MISSING IMAGE =====

        return create_placeholder(
            player_name,
            country,
            base_price
        )


    except Exception as e:

        print(
            "PLAYER IMAGE ERROR:",
            repr(e)
        )

        return create_placeholder(
            player_name,
            country,
            base_price
        )
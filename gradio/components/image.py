"""gr.Image() component."""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any, Literal

import numpy as np
import PIL
import PIL.ImageOps
from gradio_client import utils as client_utils
from gradio_client.documentation import document, set_documentation_group
from gradio_client.serializing import ImgSerializable
from PIL import Image as _Image  # using _ to minimize namespace pollution

from gradio import processing_utils, utils
from gradio.components.base import IOComponent, _Keywords
from gradio.events import (
    Changeable,
    Clearable,
    Editable,
    EventListenerMethod,
    Selectable,
    Streamable,
    Uploadable,
)
from gradio.interpretation import TokenInterpretable

set_documentation_group("component")
_Image.init()  # fixes https://github.com/gradio-app/gradio/issues/2843


@document()
class Image(
    Editable,
    Clearable,
    Changeable,
    Streamable,
    Selectable,
    Uploadable,
    IOComponent,
    ImgSerializable,
    TokenInterpretable,
):
    """
    Creates an image component that can be used to upload/draw images (as an input) or display images (as an output).
    Preprocessing: passes the uploaded image as a {numpy.array}, {PIL.Image} or {str} filepath depending on `type` -- unless `tool` is `sketch` AND source is one of `upload` or `webcam`. In these cases, a {dict} with keys `image` and `mask` is passed, and the format of the corresponding values depends on `type`.
    Postprocessing: expects a {numpy.array}, {PIL.Image} or {str} or {pathlib.Path} filepath to an image and displays the image.
    Examples-format: a {str} filepath to a local file that contains the image.
    Demos: image_mod, image_mod_default_image
    Guides: image-classification-in-pytorch, image-classification-in-tensorflow, image-classification-with-vision-transformers, building-a-pictionary_app, create-your-own-friends-with-a-gan
    """

    def __init__(
        self,
        value: str | _Image.Image | np.ndarray | None = None,
        *,
        shape: tuple[int, int] | None = None,
        height: int | None = None,
        width: int | None = None,
        image_mode: str = "RGB",
        invert_colors: bool = False,
        source: str = "upload",
        tool: str | None = None,
        type: str = "numpy",
        label: str | None = None,
        every: float | None = None,
        show_label: bool = True,
        container: bool = True,
        scale: int | None = None,
        min_width: int = 160,
        interactive: bool | None = None,
        visible: bool = True,
        streaming: bool = False,
        elem_id: str | None = None,
        elem_classes: list[str] | str | None = None,
        mirror_webcam: bool = True,
        brush_radius: float | None = None,
        **kwargs,
    ):
        """
        Parameters:
            value: A PIL Image, numpy array, path or URL for the default value that Image component is going to take. If callable, the function will be called whenever the app loads to set the initial value of the component.
            shape: (width, height) shape to crop and resize image when passed to function. If None, matches input image size. Pass None for either width or height to only crop and resize the other.
            height: Height of the displayed image in pixels.
            width: Width of the displayed image in pixels.
            image_mode: "RGB" if color, or "L" if black and white.
            invert_colors: whether to invert the image as a preprocessing step.
            source: Source of image. "upload" creates a box where user can drop an image file, "webcam" allows user to take snapshot from their webcam, "canvas" defaults to a white image that can be edited and drawn upon with tools.
            tool: Tools used for editing. "editor" allows a full screen editor (and is the default if source is "upload" or "webcam"), "select" provides a cropping and zoom tool, "sketch" allows you to create a binary sketch (and is the default if source="canvas"), and "color-sketch" allows you to created a sketch in different colors. "color-sketch" can be used with source="upload" or "webcam" to allow sketching on an image. "sketch" can also be used with "upload" or "webcam" to create a mask over an image and in that case both the image and mask are passed into the function as a dictionary with keys "image" and "mask" respectively.
            type: The format the image is converted to before being passed into the prediction function. "numpy" converts the image to a numpy array with shape (height, width, 3) and values from 0 to 255, "pil" converts the image to a PIL image object, "filepath" passes a str path to a temporary file containing the image.
            label: component name in interface.
            every: If `value` is a callable, run the function 'every' number of seconds while the client connection is open. Has no effect otherwise. Queue must be enabled. The event can be accessed (e.g. to cancel it) via this component's .load_event attribute.
            show_label: if True, will display label.
            container: If True, will place the component in a container - providing some extra padding around the border.
            scale: relative width compared to adjacent Components in a Row. For example, if Component A has scale=2, and Component B has scale=1, A will be twice as wide as B. Should be an integer.
            min_width: minimum pixel width, will wrap if not sufficient screen space to satisfy this value. If a certain scale value results in this Component being narrower than min_width, the min_width parameter will be respected first.
            interactive: if True, will allow users to upload and edit an image; if False, can only be used to display images. If not provided, this is inferred based on whether the component is used as an input or output.
            visible: If False, component will be hidden.
            streaming: If True when used in a `live` interface, will automatically stream webcam feed. Only valid is source is 'webcam'.
            elem_id: An optional string that is assigned as the id of this component in the HTML DOM. Can be used for targeting CSS styles.
            elem_classes: An optional list of strings that are assigned as the classes of this component in the HTML DOM. Can be used for targeting CSS styles.
            mirror_webcam: If True webcam will be mirrored. Default is True.
            brush_radius: Size of the brush for Sketch. Default is None which chooses a sensible default
        """
        self.brush_radius = brush_radius
        self.mirror_webcam = mirror_webcam
        valid_types = ["numpy", "pil", "filepath"]
        if type not in valid_types:
            raise ValueError(
                f"Invalid value for parameter `type`: {type}. Please choose from one of: {valid_types}"
            )
        self.type = type
        self.shape = shape
        self.height = height
        self.width = width
        self.image_mode = image_mode
        valid_sources = ["upload", "webcam", "canvas"]
        if source not in valid_sources:
            raise ValueError(
                f"Invalid value for parameter `source`: {source}. Please choose from one of: {valid_sources}"
            )
        self.source = source
        if tool is None:
            self.tool = "sketch" if source == "canvas" else "editor"
        else:
            self.tool = tool
        self.invert_colors = invert_colors
        self.streaming = streaming
        if streaming and source != "webcam":
            raise ValueError("Image streaming only available if source is 'webcam'.")
        self.select: EventListenerMethod
        """
        Event listener for when the user clicks on a pixel within the image.
        Uses event data gradio.SelectData to carry `index` to refer to the [x, y] coordinates of the clicked pixel.
        See EventData documentation on how to use this event data.
        """

        IOComponent.__init__(
            self,
            label=label,
            every=every,
            show_label=show_label,
            container=container,
            scale=scale,
            min_width=min_width,
            interactive=interactive,
            visible=visible,
            elem_id=elem_id,
            elem_classes=elem_classes,
            value=value,
            **kwargs,
        )
        TokenInterpretable.__init__(self)

    def get_config(self):
        return {
            "image_mode": self.image_mode,
            "shape": self.shape,
            "height": self.height,
            "width": self.width,
            "source": self.source,
            "tool": self.tool,
            "value": self.value,
            "streaming": self.streaming,
            "mirror_webcam": self.mirror_webcam,
            "brush_radius": self.brush_radius,
            "selectable": self.selectable,
            **IOComponent.get_config(self),
        }

    @staticmethod
    def update(
        value: Any | Literal[_Keywords.NO_VALUE] | None = _Keywords.NO_VALUE,
        height: int | None = None,
        width: int | None = None,
        label: str | None = None,
        show_label: bool | None = None,
        container: bool | None = None,
        scale: int | None = None,
        min_width: int | None = None,
        interactive: bool | None = None,
        visible: bool | None = None,
        brush_radius: float | None = None,
    ):
        return {
            "height": height,
            "width": width,
            "label": label,
            "show_label": show_label,
            "container": container,
            "scale": scale,
            "min_width": min_width,
            "interactive": interactive,
            "visible": visible,
            "value": value,
            "brush_radius": brush_radius,
            "__type__": "update",
        }

    def _format_image(
        self, im: _Image.Image | None
    ) -> np.ndarray | _Image.Image | str | None:
        """Helper method to format an image based on self.type"""
        if im is None:
            return im
        fmt = im.format
        if self.type == "pil":
            return im
        elif self.type == "numpy":
            return np.array(im)
        elif self.type == "filepath":
            path = self.pil_to_temp_file(
                im, dir=self.DEFAULT_TEMP_DIR, format=fmt or "png"
            )
            self.temp_files.add(path)
            return path
        else:
            raise ValueError(
                "Unknown type: "
                + str(self.type)
                + ". Please choose from: 'numpy', 'pil', 'filepath'."
            )

    def preprocess(
        self, x: str | dict[str, str] | dict[str, str | list[list[float]]]
    ) -> np.ndarray | _Image.Image | str | dict | None:
        """
        Parameters:
            x: base64 url data, or (if tool == "sketch") a dict of image and mask base64 url data
        Returns:
            image in requested format, or (if tool == "sketch") a dict of image and mask in requested format
        """
        if x is None:
            return x

        mask = ""
        if self.tool == "sketch" and self.source in ["upload", "webcam"]:
            assert isinstance(x, dict)
            x, mask = x["image"], x["mask"]
        
        boxes = []
        if self.tool == "boxes" and self.source in ["upload", "webcam"]:
            assert isinstance(x, dict)
            assert isinstance(x['image'], str)
            assert isinstance(x['boxes'], list)
            x, boxes = x["image"], x["boxes"]

        assert isinstance(x, str)
        im = processing_utils.decode_base64_to_image(x)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            im = im.convert(self.image_mode)
        if self.shape is not None:
            im = processing_utils.resize_and_crop(im, self.shape)
        if self.invert_colors:
            im = PIL.ImageOps.invert(im)
        if (
            self.source == "webcam"
            and self.mirror_webcam is True
            and self.tool != "color-sketch"
        ):
            im = PIL.ImageOps.mirror(im)

        if self.tool == "sketch" and self.source in ["upload", "webcam"]:
            mask_im = processing_utils.decode_base64_to_image(mask)
            return {
                "image": self._format_image(im),
                "mask": self._format_image(mask_im),
            }
        
        if self.tool == "boxes" and self.source in ["upload", "webcam"]:
            return {"image": self._format_image(im), "boxes": boxes}

        return self._format_image(im)

    def postprocess(
        self, y: np.ndarray | _Image.Image | str | Path | None
    ) -> str | None:
        """
        Parameters:
            y: image as a numpy array, PIL Image, string/Path filepath, or string URL
        Returns:
            base64 url data
        """
        if y is None:
            return None
        if isinstance(y, np.ndarray):
            return processing_utils.encode_array_to_base64(y)
        elif isinstance(y, _Image.Image):
            return processing_utils.encode_pil_to_base64(y)
        elif isinstance(y, (str, Path)):
            return client_utils.encode_url_or_file_to_base64(y)
        else:
            raise ValueError("Cannot process this value as an Image")

    def set_interpret_parameters(self, segments: int = 16):
        """
        Calculates interpretation score of image subsections by splitting the image into subsections, then using a "leave one out" method to calculate the score of each subsection by whiting out the subsection and measuring the delta of the output value.
        Parameters:
            segments: Number of interpretation segments to split image into.
        """
        self.interpretation_segments = segments
        return self

    def _segment_by_slic(self, x):
        """
        Helper method that segments an image into superpixels using slic.
        Parameters:
            x: base64 representation of an image
        """
        x = processing_utils.decode_base64_to_image(x)
        if self.shape is not None:
            x = processing_utils.resize_and_crop(x, self.shape)
        resized_and_cropped_image = np.array(x)
        try:
            from skimage.segmentation import slic
        except (ImportError, ModuleNotFoundError) as err:
            raise ValueError(
                "Error: running this interpretation for images requires scikit-image, please install it first."
            ) from err
        try:
            segments_slic = slic(
                resized_and_cropped_image,
                self.interpretation_segments,
                compactness=10,
                sigma=1,
                start_label=1,
            )
        except TypeError:  # For skimage 0.16 and older
            segments_slic = slic(
                resized_and_cropped_image,
                self.interpretation_segments,
                compactness=10,
                sigma=1,
            )
        return segments_slic, resized_and_cropped_image

    def tokenize(self, x):
        """
        Segments image into tokens, masks, and leave-one-out-tokens
        Parameters:
            x: base64 representation of an image
        Returns:
            tokens: list of tokens, used by the get_masked_input() method
            leave_one_out_tokens: list of left-out tokens, used by the get_interpretation_neighbors() method
            masks: list of masks, used by the get_interpretation_neighbors() method
        """
        segments_slic, resized_and_cropped_image = self._segment_by_slic(x)
        tokens, masks, leave_one_out_tokens = [], [], []
        replace_color = np.mean(resized_and_cropped_image, axis=(0, 1))
        for segment_value in np.unique(segments_slic):
            mask = segments_slic == segment_value
            image_screen = np.copy(resized_and_cropped_image)
            image_screen[segments_slic == segment_value] = replace_color
            leave_one_out_tokens.append(
                processing_utils.encode_array_to_base64(image_screen)
            )
            token = np.copy(resized_and_cropped_image)
            token[segments_slic != segment_value] = 0
            tokens.append(token)
            masks.append(mask)
        return tokens, leave_one_out_tokens, masks

    def get_masked_inputs(self, tokens, binary_mask_matrix):
        masked_inputs = []
        for binary_mask_vector in binary_mask_matrix:
            masked_input = np.zeros_like(tokens[0], dtype=int)
            for token, b in zip(tokens, binary_mask_vector):
                masked_input = masked_input + token * int(b)
            masked_inputs.append(processing_utils.encode_array_to_base64(masked_input))
        return masked_inputs

    def get_interpretation_scores(
        self, x, neighbors, scores, masks, tokens=None, **kwargs
    ) -> list[list[float]]:
        """
        Returns:
            A 2D array representing the interpretation score of each pixel of the image.
        """
        x = processing_utils.decode_base64_to_image(x)
        if self.shape is not None:
            x = processing_utils.resize_and_crop(x, self.shape)
        x = np.array(x)
        output_scores = np.zeros((x.shape[0], x.shape[1]))

        for score, mask in zip(scores, masks):
            output_scores += score * mask

        max_val, min_val = np.max(output_scores), np.min(output_scores)
        if max_val > 0:
            output_scores = (output_scores - min_val) / (max_val - min_val)
        return output_scores.tolist()

    def style(self, *, height: int | None = None, width: int | None = None, **kwargs):
        """
        This method is deprecated. Please set these arguments in the constructor instead.
        """
        warnings.warn(
            "The `style` method is deprecated. Please set these arguments in the constructor instead."
        )
        if height is not None:
            self.height = height
        if width is not None:
            self.width = width
        return self

    def check_streamable(self):
        if self.source != "webcam":
            raise ValueError("Image streaming only available if source is 'webcam'.")

    def as_example(self, input_data: str | None) -> str:
        if input_data is None:
            return ""
        elif (
            self.root_url
        ):  # If an externally hosted image, don't convert to absolute path
            return input_data
        return str(utils.abspath(input_data))

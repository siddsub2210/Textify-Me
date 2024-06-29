import shutil
import kivy
from kivy.clock import mainthread
from kivy.config import Config
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.app import App
from kivy.uix.slider import Slider
from kivymd.app import MDApp
import PIL
from android import mActivity, autoclass, api_version
from PIL import Image, ImageOps
from android.permissions import request_permissions, Permission
from androidstorage4kivy import SharedStorage, Chooser  # all the job is done via these two modules
import os
from kivy.lang import Builder

Environment = autoclass('android.os.Environment')

# image functions:
# ascii characters used to build the output text
ASCII_CHARS = ["@", "#", "S", "%", "?", "*", "+", ";", ":", ",", "."]


# resize image according to a new width
def resize_image(image, new_width=100):
    width, height = image.size
    ratio = height / width
    new_height = int(new_width * ratio)
    resized_image = image.resize((new_width, new_height))
    return (resized_image)
# convert each pixel to grayscale
def grayify(image):
    grayscale_image = image.convert("L")
    return (grayscale_image)
# convert pixels to a string of ascii characters
def pixels_to_ascii(image):
    pixels = image.getdata()
    characters = "".join([ASCII_CHARS[pixel // 25] for pixel in pixels])
    return (characters)


# app layout, and formatting
class MainWidget(RelativeLayout):
    path = None
    shared = None
    popup_invalid_file = None

    def __init__(self, **kwargs):
        super(RelativeLayout, self).__init__(**kwargs)
        # get the permissions needed
        request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_MEDIA_IMAGES, Permission.READ_MEDIA_VIDEO, Permission.READ_MEDIA_AUDIO])
        self.opened_file = None  # file path to load, None initially, changes later on
        #  file cache in the private storage (for cleaning purposes)
        self.cache = SharedStorage().get_cache_dir()

    def b1_on_click(self, widget):
        self.chooser_caller_func1()
        self.path = None
    @mainthread
    def chooser_caller_func1(self):
        Chooser(self.chooser_callback1).choose_content("image/*", multiple=False)
    @mainthread
    def chooser_callback1(self, uri_list):
        # Callback handling the chooser
        try:
            # print(uri_list)  # testing
            for uri in uri_list:
                # We obtain the file from the Android's "Shared storage", but we can't work with it directly.
                # We need to first copy it to our app's "Private storage." The callback receives the
                # 'android.net.Uri' rather than a usual POSIX-style file path. Calling the 'copy_from_shared'
                # method copies this file to our private storage and returns a normal file path of the
                # copied file in the private storage:
                self.path = SharedStorage().copy_from_shared(uri)
                self.uri = uri  # just to keep the uri for future reference
        except Exception as e:
            pass
        #now, resume with ascii art converting process
        self.on_resume1()

    def on_resume1(self):
        print("(testing) self.path = ", self.path)
        #self.path = SharedStorage().copy_to_shared(self.path)
        print("(testing) self.path = ",self.path,"\n")
        # We load our file when the chooser closes and our app resumes from the paused mode
        if self.path != None:
            # we can work with this file in a normal Python way
            if not (self.path.endswith("png") or self.path.endswith("jpeg") or self.path.endswith("jpg")):
                # POPUP WITH ERROR MESSAGE
                layout = BoxLayout(orientation="vertical")
                layout.add_widget(Label(text="You Must select only jpeg, jpg or png files"))
                # layout.add_widget(Button(text= "close", on_press = lambda widget: self.popup_invalid_file.dismiss()))
                self.popup_invalid_file = Popup(title="Invalid selection",
                                                content=layout,
                                                size_hint=(0.8, 0.25), pos_hint={"center_x": 0.5, "center_y": 0.5},
                                                auto_dismiss=True)
                self.popup_invalid_file.open()
            else:
                # main code here
                self.img_to_text(self.path)
        else:
            # POPUP WITH ERROR MESSAGE
            layout = BoxLayout(orientation="vertical")
            layout.add_widget(Label(text="No file was selected"))
            # layout.add_widget(Button(text="close", on_press=lambda widget: self.popup_invalid_file.dismiss()))
            self.popup_invalid_file = Popup(title="Invalid selection",
                                            content=layout,
                                            size_hint=(0.4, 0.25), pos_hint={"center_x": 0.5, "center_y": 0.5},
                                            auto_dismiss=True)
            self.popup_invalid_file.open()

            # reset the path to None
            self.path = None
            # clean the cache
        if self.cache and os.path.exists(self.cache):
            shutil.rmtree(self.cache)  # cleaning cache

    def img_to_text(self, path):
        # open image from path
        image = PIL.Image.open(path)
        # convert image to ascii
        # image = resize_image(image, 150)
        new_image_data = pixels_to_ascii(grayify(image))
        # testing purpose
        image.show()
        # format
        pixel_count = len(new_image_data)
        new_width = image.size[0]
        ascii_image = "\n".join(
            [new_image_data[index:(index + new_width)] for index in range(0, pixel_count, new_width)])

        # save result to "ascii_image.txt" in private directory... then copy it to shared storage
        # this step will be done save_file method
        self.save_file(ascii_image)

    def save_file(self, txt):
        # this function is called in im_to_txt.
        # it is used to save the new txt file from app storage to android storage
        filename = os.path.join(SharedStorage().get_cache_dir(),
                                "TextImage.txt")  # forming the path of our new file
        # creating the file in a normal way, but again in the private storage
        with open(filename, "w") as file:
            file.write(txt)

        # now we can copy it to the shared storage
        SharedStorage().copy_to_shared(private_file=filename)
        Popup(
            title="Success!",
            content=Label(
            text="TextImage.txt is stored under\nthe Documents folder in your phone's\ninternal storage."),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            size_hint=(0.8, 0.25),
            auto_dismiss=True
        ).open()

        # Note that Android copies our file to the Documents folder. It is done automatically. Why?
        # Because we created a .txt file which Android recognizes as a document. If we create an .mp3 file,
        # it will go to the Music folder, etc. Let's try it:

        # filename2 = os.path.join(SharedStorage().get_cache_dir(), "My audio track from KivyLoadSave.mp3")
        # with open(filename2, "w") as file2:
        #     file2.write("")
        # SharedStorage().copy_to_shared(private_file=filename2)

        # Check your Music folder now. Android also creates a subfolder named after your app.
        # This is the way Google now wants us to work with files and their "Collections".

        if self.cache and os.path.exists(self.cache):
            shutil.rmtree(self.cache)  # cleaning cache



class ascii_converter(App):
    def build(self):
        pass


if __name__ =="__main__":
    Builder.load_file("ascii_converter.kv")
    ascii_converter().run()
    
    

#!/usr/bin/env python
import gi, sys, getopt, subprocess as sp
from importlib import metadata
from os import path

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio

# Desabling deprecation warnings
import warnings
warnings.filterwarnings("ignore", category = DeprecationWarning)

class EjectApplet(Gtk.StatusIcon):
    def __init__(self):
        # Initializing the applet itself
        super().__init__(title = "Eject applet")
        self.set_from_icon_name("drive-harddisk-usb-symbolic")
        self.connect("activate", self.on_left_click)
        self.connect("popup-menu", self.on_right_click)

        # Initializing the volume monitor
        self.monitor = Gio.VolumeMonitor.get()
        self.monitor.connect("volume-added", self.on_volume_added)
        self.monitor.connect("volume-removed", self.on_volume_removed)

    def new_menu_item(self, label, callback, *args):
        item = Gtk.MenuItem(label = label)
        item.connect("activate", callback, *args)
        return item

    def on_volume_added(self, monitor, volume):
        volume_name = volume.get_name()
        drive_name = volume.get_drive().get_name()
        print(f"New volume: {volume_name} ({drive_name})")

    def on_volume_removed(self, monitor, volume):
        volume_name = volume.get_name()
        drive_name = volume.get_drive().get_name()
        print(f"Volume removed: {volume_name} ({drive_name})")

    def on_left_click(self, icon):
        # Defines if a volume is internal
        def is_internal(volume):
            block_path = "/sys/class/block/" + path.basename(volume.get_identifier("unix-device"))
            return not (path.islink(block_path) and "/usb" in path.realpath(block_path))

        # Creating a menu object
        menu = Gtk.Menu()

        for volume in self.monitor.get_volumes():
            for i in volume.enumerate_identifiers():
                print(i, ": ", volume.get_identifier(i), sep = "")

            # If it's an internal volume do not create a menu item
            if is_internal(volume):
                continue

            # Creating a submenu for each volume detected
            item = Gtk.MenuItem(label = volume.get_name() + " (" + volume.get_drive().get_name() + ")")
            submenu = Gtk.Menu()
            item.set_submenu(submenu)
            menu.append(item)

            # Show something if volume is not mountable
            if volume.get_mount():
                submenu.append(self.new_menu_item("Open", self.open_volume, volume))
                submenu.append(self.new_menu_item("Unmount", self.unmount, volume))
            else:
                submenu.append(self.new_menu_item("Mount", self.mount, volume))
                submenu.append(self.new_menu_item("Mount and Open", self.mount, volume, self.open_volume))

        # If no volume is detected
        if len(menu) == 0:
            dummy_item = Gtk.MenuItem(label = "No volumes detected")
            dummy_item.set_sensitive(False)
            menu.add(dummy_item)

        menu.show_all()
        menu.popup_at_pointer()

    def on_right_click(self, icon, button, time):
        menu = Gtk.Menu()
        menu.append(self.new_menu_item("About", self.show_about_dialog))
        menu.append(self.new_menu_item("Quit", Gtk.main_quit))
        menu.show_all()
        menu.popup_at_pointer()

    def mount(self, item, volume, callback = None):
        volume.mount(0, None, None, callback)
        volume_name = volume.get_name()
        drive_name = volume.get_drive().get_name()
        print(f"Mounting volume: {volume_name} ({drive_name})")

    def unmount(self, item, volume):
        volume.get_mount().unmount(0)
        volume_name = volume.get_name()
        drive_name = volume.get_drive().get_name()
        print(f"Unmounting volume: {volume_name} ({drive_name})")

    def open_volume(self, item, volume):
        # If the function is a callback from volume.mount(), fix parameters
        if type(volume) is Gio.Task:
            volume = item

        volume_name = volume.get_name()
        drive_name = volume.get_drive().get_name()
        print(f"Opening volume: {volume_name} ({drive_name})")

        # TODO: fork the application and to keep it alive when eject-applet is killed
        volume_uri = volume.get_mount().get_root().get_uri()
        sp.run(["xdg-open", volume_uri])

    def show_about_dialog(self, widget):
        dialog = Gtk.AboutDialog()
        dialog.set_destroy_with_parent(True)
        dialog.set_name("Eject applet")
        dialog.set_comments("A simple external disk management application that sits in the tray.")
        dialog.set_website("http://github.com/Akmadan23/eject-applet")
        dialog.set_version(metadata.version("eject-applet"))
        dialog.set_authors(["Azad Ahmadi", "Shrikant Sharat Kandula"])
        dialog.set_license("GPL-3 License (https://www.gnu.org/licenses/gpl-3.0.en.html)")

        dialog.run()
        dialog.destroy()

def main():
    try:
        # Parsing options and arguments
        opts, args = getopt.getopt(sys.argv[1:], "hv", ["help", "version"])
    except getopt.GetoptError as e:
        print("[ERROR]", e)
        sys.exit(2)

    # Handling options
    for o, a in opts:
        if o in ["-h", "--help"]:
            f = open(path.dirname(__file__) + "/data/help.txt", "r")
            print(f.read())
            f.close()
            sys.exit()
        elif o in ["-v", "--version"]:
            print("eject-applet", metadata.version("eject-applet"))
            sys.exit()

    # Handling arguments (not supported)
    for a in args:
        print("[WARNING] Unknown argument:", a)

    try:
        EjectApplet()
        Gtk.main()
    except KeyboardInterrupt:
        print("\n[WARNING] Interrupted by user.")

if __name__ == "__main__":
    main()

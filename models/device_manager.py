"""
Modelo de gestión de dispositivos
Maneja la lógica de negocio relacionada con dispositivos
"""

import json
from pathlib import Path


class DeviceManager:
    """
    Mantiene los dispositivos organizados por zona.
    devices_by_zone: { zona: [device_dict, ...] }
    cada device_dict: {"id": str, "tipo": str, "zona": str, "active": bool, ...}
    """

    def __init__(self, devices_file=None):
        self.devices_file = devices_file
        self.devices_by_zone = {}

        # Si se proporciona un archivo, cargar datos
        if self.devices_file:
            self.load_devices()

    def set_devices_file(self, file_path):
        """Establece el archivo de dispositivos y carga los datos"""
        self.devices_file = file_path
        self.load_devices()

    def load_devices(self):
        """Carga dispositivos desde el archivo JSON"""
        if not self.devices_file:
            return

        file_path = Path(self.devices_file)
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.devices_by_zone = data.get("devices_by_zone", {})
            except:
                self.devices_by_zone = {}
        else:
            self.devices_by_zone = {}

    def save_devices(self):
        """Guarda dispositivos en el archivo JSON"""
        if not self.devices_file:
            return

        file_path = Path(self.devices_file)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(
                {"devices_by_zone": self.devices_by_zone},
                f,
                indent=4,
                ensure_ascii=False
            )

    def add_device(self, device):
        """Agrega un dispositivo a una zona específica"""
        zone = device["zona"]
        if zone not in self.devices_by_zone:
            self.devices_by_zone[zone] = []
        self.devices_by_zone[zone].append(device)
        self.save_devices()  # Guardar después de agregar

    def delete_device(self, device):
        """Elimina un dispositivo de su zona"""
        z = device["zona"]
        if z in self.devices_by_zone:
            try:
                self.devices_by_zone[z].remove(device)
            except ValueError:
                pass
            if not self.devices_by_zone[z]:
                del self.devices_by_zone[z]
        self.save_devices()  # Guardar después de eliminar

    def move_device_zone(self, device, new_zone):
        """Mueve un dispositivo de una zona a otra"""
        old = device["zona"]
        if old in self.devices_by_zone and device in self.devices_by_zone[old]:
            self.devices_by_zone[old].remove(device)
            if not self.devices_by_zone[old]:
                del self.devices_by_zone[old]
        device["zona"] = new_zone
        if new_zone not in self.devices_by_zone:
            self.devices_by_zone[new_zone] = []
        self.devices_by_zone[new_zone].append(device)
        self.save_devices()  # Guardar después de mover

    def get_zones(self):
        """Retorna lista ordenada de zonas"""
        return sorted(list(self.devices_by_zone.keys()))

    def all_devices(self):
        """Retorna lista plana de todos los dispositivos"""
        out = []
        for z, lst in self.devices_by_zone.items():
            out.extend(lst)
        return out
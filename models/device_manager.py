"""
Modelo de gestión de dispositivos
Maneja la lógica de negocio relacionada con dispositivos
"""

class DeviceManager:
    """
    Mantiene los dispositivos organizados por zona.
    devices_by_zone: { zona: [device_dict, ...] }
    cada device_dict: {"id": str, "tipo": str, "zona": str, "active": bool, ...}
    """
    def __init__(self):
        self.devices_by_zone = {}

    def add_device(self, device):
        """Agrega un dispositivo a una zona específica"""
        zone = device["zona"]
        if zone not in self.devices_by_zone:
            self.devices_by_zone[zone] = []
        self.devices_by_zone[zone].append(device)

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

    def get_zones(self):
        """Retorna lista ordenada de zonas"""
        return sorted(list(self.devices_by_zone.keys()))

    def all_devices(self):
        """Retorna lista plana de todos los dispositivos"""
        out = []
        for z, lst in self.devices_by_zone.items():
            out.extend(lst)
        return out

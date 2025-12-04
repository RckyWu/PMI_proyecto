"""
Script de diagnóstico: Interceptar y mostrar TODOS los comandos que se envían
"""

import sys
import os

# Agregar el directorio del proyecto al path
sys.path.insert(0, os.getcwd())

from controllers.serial_comm import get_serial_communicator
import time

def test_activacion_desde_app():
    print("=" * 80)
    print("DIAGNÓSTICO: Activación desde la Aplicación")
    print("=" * 80)
    
    # Obtener el serial_comm (mismo que usa la app)
    serial_comm = get_serial_communicator()
    
    # Verificar estado
    print(f"\n1. ¿Serial disponible? {serial_comm is not None}")
    
    if not serial_comm:
        print("\n❌ PROBLEMA CRÍTICO:")
        print("   get_serial_communicator() retornó None")
        print("   La aplicación no puede enviar comandos")
        return False
    
    print(f"2. ¿Conectado? {serial_comm.is_connected()}")
    
    if not serial_comm.is_connected():
        print("\n❌ PROBLEMA CRÍTICO:")
        print("   serial_comm no está conectado")
        print("   Verifica que:")
        print("   - El Pico esté conectado a COM5")
        print("   - El puerto no esté ocupado")
        return False
    
    print(f"3. Puerto: {serial_comm.puerto if hasattr(serial_comm, 'puerto') else 'Desconocido'}")
    print(f"4. Baud: {serial_comm.baud if hasattr(serial_comm, 'baud') else 'Desconocido'}")
    
    # Test: Enviar comando de activación
    print("\n" + "=" * 80)
    print("TEST: Activar PIR usando serial_comm.activar_dispositivo()")
    print("=" * 80)
    
    print("\n📤 Llamando: serial_comm.activar_dispositivo('pir')")
    resultado = serial_comm.activar_dispositivo("pir")
    
    print(f"   Resultado: {resultado}")
    
    if not resultado:
        print("\n❌ PROBLEMA:")
        print("   activar_dispositivo() retornó False")
        print("   El comando NO se envió")
        return False
    
    print("✅ Comando enviado (según activar_dispositivo)")
    
    # Esperar respuesta
    print("\n⏳ Esperando respuesta del Pico (3 segundos)...")
    time.sleep(3)
    
    # Leer eventos
    eventos_recibidos = []
    for _ in range(10):  # Intentar leer hasta 10 eventos
        evento = serial_comm.get_event()
        if evento:
            print(f"📥 Evento: {evento}")
            eventos_recibidos.append(evento)
        time.sleep(0.1)
    
    if not eventos_recibidos:
        print("\n⚠️ No se recibieron eventos")
        print("   Posibles causas:")
        print("   1. El Pico no respondió")
        print("   2. El comando no llegó")
        print("   3. El hilo de lectura no está funcionando")
        return False
    
    # Verificar si hay OK:ACTIVADO:PIR
    ok_recibido = any("OK:ACTIVADO:PIR" in e for e in eventos_recibidos)
    
    if ok_recibido:
        print("\n✅ Pico respondió con OK:ACTIVADO:PIR")
    else:
        print("\n⚠️ No se recibió OK:ACTIVADO:PIR")
        print(f"   Se recibieron {len(eventos_recibidos)} mensajes pero no la confirmación")
    
    # Test: Generar evento
    print("\n" + "=" * 80)
    print("TEST: Generar evento con PIR activado")
    print("=" * 80)
    print("👋 Mueve tu mano frente al sensor PIR")
    print("⏳ Esperando 10 segundos...\n")
    
    eventos_pir = []
    for _ in range(100):  # 100 * 0.1s = 10 segundos
        evento = serial_comm.get_event()
        if evento:
            if "EVENT:PIR:DETECTADO" in evento:
                print(f"📥 {evento}")
                eventos_pir.append(evento)
            elif not evento.startswith("HEARTBEAT"):
                print(f"📥 {evento}")
        time.sleep(0.1)
    
    if eventos_pir:
        print(f"\n✅ PIR generó {len(eventos_pir)} eventos")
        print("\n🎉 ¡EL SISTEMA FUNCIONA!")
        print("   Si en tu aplicación no ves eventos, verifica:")
        print("   1. Que main_menu.py esté llamando a _process_device_messages()")
        print("   2. Que _handle_device_event() procese correctamente los eventos")
        return True
    else:
        print("\n❌ PIR NO generó eventos")
        print("\n🔧 Posibles causas:")
        print("   1. PIR no se activó realmente")
        print("   2. Sensor PIR no conectado")
        print("   3. No hubo movimiento suficiente")
        
        # Verificar estado
        print("\n📤 Verificando estado con CMD:STATUS...")
        serial_comm.send_command("CMD:STATUS")
        time.sleep(1)
        
        for _ in range(10):
            evento = serial_comm.get_event()
            if evento and "STATUS:" in evento:
                print(f"📊 {evento}")
                if "PIR=ON" in evento:
                    print("   ✅ PIR está ON en el Pico")
                elif "PIR=OFF" in evento:
                    print("   ❌ PIR está OFF en el Pico (no se activó)")
                break
            time.sleep(0.1)
        
        return False

if __name__ == "__main__":
    print("\n🔍 Este script verificará:")
    print("   1. Si get_serial_communicator() funciona")
    print("   2. Si está conectado")
    print("   3. Si activar_dispositivo() envía el comando")
    print("   4. Si el Pico responde")
    print("   5. Si se generan eventos")
    print()
    print("⚠️  IMPORTANTE:")
    print("   - Ejecuta desde el directorio del proyecto")
    print("   - Cierra Thonny antes de ejecutar")
    print("   - La aplicación Python NO debe estar ejecutándose")
    print()
    
    input("Presiona Enter para comenzar...")
    
    # Cambiar al directorio del proyecto si es necesario
    if not os.path.exists("controllers"):
        print("\n❌ No se encuentra la carpeta 'controllers'")
        print("   Ejecuta este script desde:")
        print("   C:\\Users\\Brandon\\OneDrive\\Desktop\\PMI_proyecto-main")
        input("\nPresiona Enter para salir...")
        sys.exit(1)
    
    test_activacion_desde_app()
    
    input("\nPresiona Enter para salir...")

"""
Punto de entrada de la aplicación Ving
Ejecuta la interfaz gráfica
"""

from controllers import App


def main():
    """Función principal que inicia la aplicación"""
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()

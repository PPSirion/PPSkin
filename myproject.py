import numpy as np
import glfw
from OpenGL.GL import *
from OpenGL.GLU import *
import imgui
from imgui.integrations.glfw import GlfwRenderer
import colorsys

# Parametri del piano e dell'onda
plane_size = 50
window_size = (800, 600)
plane_height = np.zeros((plane_size, plane_size))
plane_velocity = np.zeros((plane_size, plane_size))
plane_acceleration = np.zeros((plane_size, plane_size))

# Parametri di simulazione
elasticity = 0.3 # Coefficiente di elasticità
damping = 0.7    # Coefficiente di smorzamento
delta_time = 1.0  # Passo di tempo per la simulazione
force = 3.0      # Forza applicata al clic del mouse

# Controlli della telecamera
class Camera:
    def __init__(self, angle_x=-60, angle_y=20, zoom=-25):
        self.angle_x = angle_x
        self.angle_y = angle_y
        self.zoom = zoom
        self.last_pos = None

    def update_rotation(self, x, y):
        if self.last_pos is not None:
            dx = x - self.last_pos[0]
            dy = y - self.last_pos[1]
            self.angle_y += dx * 0.2
            self.angle_x += dy * 0.2
        self.last_pos = (x, y)

    def reset_last_pos(self):
        self.last_pos = None

camera = Camera()

mouse_dragging = False
mouse_weight_active = False

def get_hex_offset(x):
    """Restituisce l'offset per la griglia esagonale."""
    return (x % 2) * 0.5

def update_plane():
    global plane_height, plane_velocity, plane_acceleration
    # Applica il peso se il mouse è premuto
    if mouse_weight_active:
        apply_force_at_cursor(glfw.get_current_context())
    laplacian = np.zeros((plane_size, plane_size))
    laplacian[1:-1, 1:-1] = (plane_height[:-2, 1:-1] + plane_height[2:, 1:-1] +
                              plane_height[1:-1, :-2] + plane_height[1:-1, 2:] - 4 * plane_height[1:-1, 1:-1])
    plane_acceleration = elasticity * laplacian - damping * plane_velocity
    plane_velocity += plane_acceleration * delta_time
    plane_height += plane_velocity * delta_time

def mouse_button_callback(window, button, action, mods):
    global mouse_dragging, mouse_weight_active
    if button == glfw.MOUSE_BUTTON_LEFT:
        if action == glfw.PRESS:
            mouse_dragging = True
            mouse_weight_active = True
            apply_force_at_cursor(window)
        elif action == glfw.RELEASE:
            mouse_dragging = False
            mouse_weight_active = False

def cursor_position_callback(window, xpos, ypos):
    global mouse_dragging
    if mouse_dragging:
        apply_force_at_cursor(window)

def apply_force_at_cursor(window):
    global plane_height
    x, y = glfw.get_cursor_pos(window)
    grid_x = int(plane_size * (x / window_size[0]))
    grid_y = int(plane_size * (1 - y / window_size[1]))
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            gx, gy = grid_x + dx, grid_y + dy
            if 0 <= gx < plane_size and 0 <= gy < plane_size:
                plane_height[gx, gy] -= force

def setup_lighting_and_color():
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    glLightfv(GL_LIGHT0, GL_POSITION, np.array([1.0, 1.0, 1.0, 0.0]))
    glPointSize(3)

def get_color(z):
    # Colore stabile per ogni altezza: mappa lineare da blu (basso) a rosso (alto)
    max_abs = 2.0  # imposta la gamma di altezze attesa
    z_norm = max(-max_abs, min(max_abs, z))
    if abs(z_norm) < 0.01:
        return (1.0, 1.0, 1.0)
    # Hue da 0.6 (blu) a 0.0 (rosso)
    h = 0.6 - 0.6 * ((z_norm + max_abs) / (2 * max_abs))
    s = min(1.0, abs(z_norm) / max_abs)
    v = 1.0
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (r, g, b)

def draw_plane():
    glBegin(GL_POINTS)
    for x in range(plane_size):
        for y in range(plane_size):
            z = plane_height[x, y]
            glColor3f(*get_color(z))
            glVertex3f(x, y + get_hex_offset(x), z)
    glEnd()

def draw_empty_hexagons():
    glBegin(GL_LINES)
    for x in range(plane_size):
        for y in range(plane_size):
            z = plane_height[x, y]
            glColor3f(*get_color(z))
            for i in range(6):
                angle = i * np.pi / 3
                x_offset = np.cos(angle)
                y_offset = np.sin(angle)
                x1 = x + 0.5 * x_offset
                y1 = y + 0.5 * y_offset + get_hex_offset(x)
                z1 = z
                x2 = x + 0.5 * np.cos(angle + np.pi / 3)
                y2 = y + 0.5 * np.sin(angle + np.pi / 3) + get_hex_offset(x)
                z2 = z
                glVertex3f(x1, y1, z1)
                glVertex3f(x2, y2, z2)
    glEnd()

def cleanup():
    glDisable(GL_LIGHTING)
    glDisable(GL_COLOR_MATERIAL)
    glDisable(GL_DEPTH_TEST)

def main():
    global elasticity, damping, delta_time, force

    if not glfw.init():
        return

    # Ottieni il monitor primario e la sua risoluzione
    monitor = glfw.get_primary_monitor()
    mode = glfw.get_video_mode(monitor)
    fullscreen_size = (mode.size.width, mode.size.height)

    # Imposta la finestra come non decorata (senza bordi)
    window = glfw.create_window(fullscreen_size[0], fullscreen_size[1], "Griglia 3D Fisica", None, None)
    if not window:
        glfw.terminate()
        return

    # Aggiorna window_size per la simulazione e la conversione coordinate mouse
    global window_size
    window_size = fullscreen_size

    glfw.make_context_current(window)
    glfw.set_mouse_button_callback(window, mouse_button_callback)
    glfw.set_cursor_pos_callback(window, cursor_position_callback)
    glEnable(GL_DEPTH_TEST)

    imgui.create_context()
    impl = GlfwRenderer(window)

    while not glfw.window_should_close(window):
        glfw.poll_events()
        impl.process_inputs()
        imgui.new_frame()

        # Finestra ImGui per i parametri
        imgui.begin("Parametri")
        _, elasticity = imgui.slider_float("Elasticità", elasticity, 0.1, 1.0)
        _, damping = imgui.slider_float("Smorzamento", damping, 0.01, 1)
        _, delta_time = imgui.slider_float("Delta Time", delta_time, 0.01, 2.0)
        _, force = imgui.slider_float("Forza", force, 0.1, 5.0)
        imgui.text("Telecamera: Trascina il tasto destro del mouse per ruotare, scorri per zoomare")
        imgui.end()

        # Controlli della telecamera (ruota con il tasto destro del mouse)
        if glfw.get_mouse_button(window, glfw.MOUSE_BUTTON_RIGHT) == glfw.PRESS:
            x, y = glfw.get_cursor_pos(window)
            camera.update_rotation(x, y)
        else:
            camera.reset_last_pos()

        update_plane()

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        gluPerspective(40, (window_size[0] / window_size[1]), 0.1, 100.0)
        glTranslatef(-25, -10, camera.zoom)
        glRotatef(camera.angle_x, 1, 0, 0)
        glRotatef(camera.angle_y, 0, 0, 1)
        glTranslatef(8, 0, 0)

        setup_lighting_and_color()
        draw_plane()
        draw_empty_hexagons()

        imgui.render()
        impl.render(imgui.get_draw_data())
        glfw.swap_buffers(window)

    cleanup()
    impl.shutdown()
    glfw.terminate()

if __name__ == "__main__":
    main()
    cleanup()
    glfw.terminate()
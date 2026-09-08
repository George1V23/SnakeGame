from kivy.properties import BooleanProperty, NumericProperty, ListProperty
from kivy.uix.widget import Widget
from kivy.core.window import Window


# Create a square for drawing
class Square(Widget):
    color = ListProperty([1, 1, 1])
    show_collision_margin = BooleanProperty(True)  # draws exact square collision boundary


# Create a triangle for drawing
class Triangle(Widget):
    angle = NumericProperty(0)
    color = ListProperty([1, 1, 1])
    show_collision_margin = BooleanProperty(True)  # draws exact head widget collision boundary


# Node for Linked List
class Node:
    def __init__(self, widget=None, next_node=None, prev_node=None):
        self.widget = widget
        self.next = next_node
        self.prev = prev_node


# Linked list class representing the snake's body
class Snake:
    def __init__(self, color_factor=0.85, step=25):
        self.head = Node(Triangle())
        self.tail = Node(Square())
        self.head.next = self.tail
        self.tail.prev = self.head
        self.size = 2
        self.color_factor = color_factor
        self.step = step
        self._apply_color(self.tail)

    @staticmethod
    def _angle_to_direction(angle):
        if angle == 0:
            return (0, 1)
        elif angle == 90:
            return (-1, 0)
        elif angle == 180:
            return (0, -1)
        elif angle == 270:
            return (1, 0)
        return (0, 1)

    def _apply_color(self, node):
        if (self.head and self.head.widget and hasattr(self.head.widget, 'color')
                and node.widget and hasattr(node.widget, 'color')):
            head_color = self.head.widget.color
            tail_index = max(1, self.size - 1)
            node.widget.color = [
                min(1.0, max(0.0, c * (self.color_factor ** tail_index)))
                for c in head_color[:3]
            ] + (list(head_color[3:]) if len(head_color) > 3 else [])

    def position_initial_tail(self):
        if not self.head or not self.head.widget or not self.tail or not self.tail.widget or self.head == self.tail:
            return
        angle = getattr(self.head.widget, 'angle', 0)
        dir_x, dir_y = self._angle_to_direction(angle)
        win_w = Window.width if Window else 800
        win_h = Window.height if Window else 600
        self.tail.widget.center = (
            (self.head.widget.center_x - dir_x * self.step) % win_w,
            (self.head.widget.center_y - dir_y * self.step) % win_h,
        )

    def _position_node(self, node):
        if not node or not node.widget or not node.prev or not node.prev.widget:
            return
        last = node.prev
        prev = last.prev
        win_w = Window.width if Window else 800
        win_h = Window.height if Window else 600

        if prev and prev.widget:
            diff_x = last.widget.center_x - prev.widget.center_x
            diff_y = last.widget.center_y - prev.widget.center_y
            if win_w > 0:
                if diff_x > win_w / 2:
                    diff_x -= win_w
                elif diff_x < -win_w / 2:
                    diff_x += win_w
            if win_h > 0:
                if diff_y > win_h / 2:
                    diff_y -= win_h
                elif diff_y < -win_h / 2:
                    diff_y += win_h
            if diff_x == 0 and diff_y == 0 and self.head and self.head.widget:
                angle = getattr(self.head.widget, 'angle', 0)
                dir_x, dir_y = self._angle_to_direction(angle)
                diff_x = -dir_x * self.step
                diff_y = -dir_y * self.step
        elif self.head and self.head.widget:
            angle = getattr(self.head.widget, 'angle', 0)
            dir_x, dir_y = self._angle_to_direction(angle)
            diff_x = -dir_x * self.step
            diff_y = -dir_y * self.step
        else:
            diff_x = 0
            diff_y = -self.step

        node.widget.center = (
            (last.widget.center_x + diff_x) % win_w,
            (last.widget.center_y + diff_y) % win_h,
        )

    def grow(self, widget=None):
        if widget is None:
            widget = Square()
        node = widget if isinstance(widget, Node) else Node(widget)
        if self.head is None:
            self.head = node
            self.tail = node
            self.size = 1
        else:
            self.tail.next = node
            node.prev = self.tail
            self.tail = node
            self.size += 1
            self._apply_color(node)
            self._position_node(node)
        return node

    def __len__(self):
        return self.size

    def __iter__(self):
        curr = self.head
        while curr:
            yield curr
            curr = curr.next

    def update_positions(self, new_head_center):
        curr = self.tail
        while curr and curr.prev:
            curr.widget.center = curr.prev.widget.center
            curr = curr.prev
        if self.head and self.head.widget:
            self.head.widget.center = new_head_center

    @staticmethod
    def _widgets_collide(first, second):
        """Return True when two widgets' real rectangular bounds overlap."""
        if not first or not second:
            return False

        return (
            first.x < second.right and
            first.right > second.x and
            first.y < second.top and
            first.top > second.y
        )

    def check_collision(self):
        """
        Check collision between the snake head and its own tail/body.

        The red boundary line and this logic use the same widget edges:
        x, y, right, and top.
        """
        if not self.head or not self.head.widget:
            return False

        head_widget = self.head.widget
        curr = self.head.next

        while curr:
            if self._widgets_collide(head_widget, curr.widget):
                return True
            curr = curr.next

        return False

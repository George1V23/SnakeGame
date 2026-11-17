from kivy.animation import Animation
from kivy.properties import BooleanProperty, NumericProperty, ListProperty
from kivy.uix.widget import Widget
from scale import STEP, UI_SCALE, field_size

SWALLOW_BULGE = 4 * UI_SCALE  # extra pixels drawn on each side of a segment carrying swallowed food


# Create a square for drawing
class Square(Widget):
    color = ListProperty([1, 1, 1])
    show_collision_margin = BooleanProperty(True)  # draws exact square collision boundary
    bulge = NumericProperty(0)  # visual-only enlargement; collision still uses the widget bounds


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
    def __init__(self, color_factor=0.85, step=STEP):
        self.head = Node(Triangle())
        self.tail = Node(Square())
        self.head.next = self.tail
        self.tail.prev = self.head

        self.size = 2
        self.step = step
        self.meals = []  # body index currently carrying each swallowed food (0 = head)

        self.color_factor = color_factor
        self.i_color = 1 #color variation it reached
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
        #if (self.head and self.head.widget and hasattr(self.head.widget, 'color')
        #        and node.widget and hasattr(node.widget, 'color')):
        head_color = self.head.widget.color
        scaled_rgb = [
            c * (self.color_factor ** self.i_color)
            for c in head_color[:3]
        ]

        #check intensity increased or lowered
        prev_color = self.tail.prev.widget.color
        intensity_increase = (prev_color[0] <= scaled_rgb[0] and prev_color[1] <= scaled_rgb[1] and prev_color[2] <= scaled_rgb[2])

        if all(c >= 0.90 for c in scaled_rgb) and intensity_increase:
            self.i_color += 2
            scaled_rgb = [c*(self.color_factor**self.i_color) for c in head_color[:3]]
            intensity_increase = False
        elif all(c <= 0.10 for c in scaled_rgb) and not intensity_increase:
            self.i_color -= 2
            scaled_rgb = [c*(self.color_factor**self.i_color) for c in head_color[:3]]
            intensity_increase = True

        node.widget.color = [
                                min(1.0, max(0.0, c))
                                for c in scaled_rgb
                            ] + (list(head_color[3:]) if len(head_color) > 3 else [])

        if intensity_increase:
            self.i_color -= 1
        else: # prev_color[0] >= scaled_rgb[0] and prev_color[1] >= scaled_rgb[1] and prev_color[2] >= scaled_rgb[2]:
            self.i_color += 1

    def position_initial_tail(self):
        if not self.head or not self.head.widget or not self.tail or not self.tail.widget or self.head == self.tail:
            return
        angle = getattr(self.head.widget, 'angle', 0)
        dir_x, dir_y = self._angle_to_direction(angle)
        win_w, win_h = field_size()
        self.tail.widget.center = (
            (self.head.widget.center_x - dir_x * self.step) % win_w,
            (self.head.widget.center_y - dir_y * self.step) % win_h,
        )

    def _position_node(self, node):
        if not node or not node.widget or not node.prev or not node.prev.widget:
            return
        last = node.prev
        prev = last.prev
        win_w, win_h = field_size()

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

    def grow(self, widget=None, center=None):
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
            if center is None:
                self._position_node(node)
            else:
                node.widget.center = center
        return node

    def swallow(self):
        """Start digesting a food just eaten by the head."""
        self.meals.append(0)

    def shrink(self, count, min_size=4):
        """Cut up to `count` segments off the tail, keeping at least `min_size` nodes; return removed widgets."""
        removed = []
        while count > 0 and self.size > min_size:
            node = self.tail
            self.tail = node.prev
            self.tail.next = None
            node.prev = None
            self.size -= 1
            removed.append(node.widget)
            count -= 1
        self.meals = [i for i in self.meals if i < self.size]  # food in the cut part is lost
        return removed

    def _digest(self, old_tail_center, interval):
        """
        Move every swallowed food one segment back along the body and enlarge the segments
        that carry one. A food that has passed the old tail becomes a new tail segment,
        placed where the tail was, which is the spot where the food was eaten.
        """
        self.meals = [i + 1 for i in self.meals]
        finished = sum(1 for i in self.meals if i >= self.size)
        self.meals = [i for i in self.meals if i < self.size]

        carrying = set(self.meals)
        duration = max(0.05, interval * 0.6)
        for index, node in enumerate(self):
            widget = node.widget
            if not hasattr(widget, 'bulge'):
                continue
            target = SWALLOW_BULGE if index in carrying else 0
            if widget.bulge != target:
                Animation.cancel_all(widget, 'bulge')
                Animation(bulge=target, duration=duration, t='out_quad').start(widget)

        new_nodes = []
        for _ in range(finished):
            node = self.grow(center=old_tail_center)
            node.widget.bulge = -node.widget.width / 2  # pop in from nothing
            Animation(bulge=0, duration=duration, t='out_back').start(node.widget)
            new_nodes.append(node)
        return new_nodes

    def __len__(self):
        return self.size

    def __iter__(self):
        curr = self.head
        while curr:
            yield curr
            curr = curr.next

    def update_positions(self, new_head_center, interval=0.1):
        """Advance the body one step; return the nodes grown from fully digested food."""
        old_tail_center = tuple(self.tail.widget.center)
        curr = self.tail
        while curr and curr.prev:
            curr.widget.center = curr.prev.widget.center
            curr = curr.prev
        if self.head and self.head.widget:
            self.head.widget.center = new_head_center
        return self._digest(old_tail_center, interval)

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

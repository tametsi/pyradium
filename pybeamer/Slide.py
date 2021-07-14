#	pybeamer - HTML presentation/slide show generator
#	Copyright (C) 2015-2021 Johannes Bauer
#
#	This file is part of pybeamer.
#
#	pybeamer is free software; you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation; this program is ONLY licensed under
#	version 3 of the License, later versions are explicitly excluded.
#
#	pybeamer is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with pybeamer; if not, write to the Free Software
#	Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#	Johannes Bauer <JohannesBauer@gmx.de>

from .Tools import XMLTools
from .Exceptions import UndefinedContentException
from .BaseDirective import BaseDirective
from .RenderableSlide import RenderableSlide
from .PauseRenderer import PauseRenderer
from pybeamer.xmlhooks.XMLHookRegistry import XMLHookRegistry

class RenderSlideDirective(BaseDirective):
	def __init__(self, xmlnode):
		assert(xmlnode.tagName == "slide")
		self._dom = xmlnode
		if not self._dom.hasAttribute("type"):
			self._dom.setAttribute("type", "default")
		self._xml_slide_vars = self._get_xml_slide_vars()
		self._content_containers = { }
		for content_node in XMLTools.findall(self._dom, "s:content"):
			self._content_containers[content_node.getAttribute("name")] = content_node
		if len(self._content_containers) == 0:
			self._content_containers["default"] = self._dom

#	@property
#	def containers(self):
#		return self._content_containers

#	def clone_containers(self):
#		return { name: container.cloneNode(deep = True) for (name, container) in self._content_containers.items() }

	@property
	def slide_type(self):
		return self._dom.getAttribute("type")

	def _get_xml_slide_vars(self):
		# First search DOM for any variables
		slide_vars = { }
		for node in XMLTools.findall(self._dom, "s:var"):
			(key, value) = (node.getAttribute("name"), node.getAttribute("value"))
			slide_vars[key] = value
			XMLTools.remove_node(node)
		return slide_vars

	def compute_slide_vars(self, rendered_presentation, sub_slide_index):
		slide_vars = dict(self._xml_slide_vars)
		slide_vars.update({
			"current_slide_number":	rendered_presentation.current_slide_number,
			"total_slide_count":	rendered_presentation.total_slide_count,
			"chapter":				rendered_presentation.toc.current_text(0),
			"section":				rendered_presentation.toc.current_text(1),
			"subsection":			rendered_presentation.toc.current_text(2),
			"toc":					rendered_presentation.frozen_toc,
			"sub_slide_index":		sub_slide_index,
		})
		return slide_vars

	def emit_slide(self, rendered_presentation, content_containers, additional_slide_vars = None):
		rendered_presentation.advance_slide()
		paused_containers = PauseRenderer(content_containers, honor_pauses = rendered_presentation.renderer.rendering_params.honor_pauses).render()

		for (sub_slide_index, paused_container) in enumerate(paused_containers):
			for container_node in paused_container.values():
				XMLHookRegistry.mangle(rendered_presentation, container_node)

			slide_vars = self.compute_slide_vars(rendered_presentation, sub_slide_index)
			if additional_slide_vars is not None:
				slide_vars.update(additional_slide_vars)
			yield RenderableSlide(slide_type = self.slide_type, content_containers = paused_container, slide_vars = slide_vars)

	def render(self, rendered_presentation):
		controller = rendered_presentation.renderer.controllers.get_controller(self, self._content_containers, rendered_presentation)
		if controller is None:
			yield from self.emit_slide(rendered_presentation, self._content_containers)
		else:
			yield from controller.render()

	def __repr__(self):
		return "Slide<%s>" % (self.slide_type)

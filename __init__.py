# -*- coding: utf-8 -*-
"""
/***************************************************************************
 LeakDetection
                                 A QGIS plugin
 This plugin is used to find leakage in water network using sensor data as input.
                             -------------------
        begin                : 2017-02-06
        copyright            : (C) 2017 by Nancy_Kapri
        email                : nancypesit@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load LeakDetection class from file LeakDetection.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .leak_detection import LeakDetection
    return LeakDetection(iface)

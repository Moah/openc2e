/*
 *  sprImage.cpp
 *  openc2e
 *
 *  Created by Alyssa Milburn on Sun Nov 19 2006.
 *  Copyright (c) 2006 Alyssa Milburn. All rights reserved.
 *
 *  This library is free software; you can redistribute it and/or
 *  modify it under the terms of the GNU Lesser General Public
 *  License as published by the Free Software Foundation; either
 *  version 2 of the License, or (at your option) any later version.
 *
 *  This library is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 *  Lesser General Public License for more details.
 *
 */

#include "openc2e.h"
#include "endianlove.h"
#include "sprImage.h"
#include <iostream>

sprImage::sprImage(std::ifstream &in, std::string n) : creaturesImage(n) {
	imgformat = if_paletted;

	m_numframes = read16le(in);

	widths.resize(m_numframes);
	heights.resize(m_numframes);
	std::vector<uint32_t> offsets(m_numframes);
	buffers.resize(m_numframes);

	for (unsigned int i = 0; i < m_numframes; i++) {
		offsets[i] = read32le(in);
		widths[i] = read16le(in);
		heights[i] = read16le(in);
	}

	// check for Terra Nornia's corrupt background sprite
	if (n == "buro") {
		// apply stupid hack for corrupt offset tables in SPR files
		// Only works if the file has 'normal' offsets we can predict, but this will only be called
		// on known files anyway.
		// TODO: can't we have a better check, eg checking if offsets are identical?
		std::cout << "Applying hack for probably-corrupt Terra Nornia background." << std::endl;
		unsigned int currpos = 2 + (8 * m_numframes);
		for (unsigned int i = 0; i < m_numframes; i++) {
			offsets[i] = currpos;
			currpos += widths[i] * heights[i];
		}
	}

	for (unsigned int i = 0; i < m_numframes; i++) {
		in.seekg(offsets[i]);
		buffers[i].resize(widths[i] * heights[i]);
		in.read(reinterpret_cast<char*>(buffers[i].data()), widths[i] * heights[i]);
	}
}

sprImage::~sprImage() {}

/* vim: set noet: */

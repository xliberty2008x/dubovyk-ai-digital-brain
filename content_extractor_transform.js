// Content Extractor Transform Node for AI Copywriter
// Separates content for LLM processing and metadata for tool use
// Formats as RAW TEXT to prevent memory issues

const items = $input.all();

return items.map(item => {
    const input = item.json;
    
    // Initialize separate sections
    let mainContent = '';
    const metadata = [];
    
    // Check if this is from Enhanced Telegram Parser
    if (input && input.contentSummary) {
        // Extract main content (text or caption) for LLM processing
        if (input.contentSummary.text) {
            mainContent = input.contentSummary.text;
        } else if (input.contentSummary.caption) {
            mainContent = input.contentSummary.caption;
        }
        
        // Add media metadata for tool use (not for final text)
        if (input.media) {
            if (input.media.fileId) {
                metadata.push(`FILE_ID: ${input.media.fileId}`);
            } else if (input.media.largestPhoto?.file_id) {
                metadata.push(`FILE_ID: ${input.media.largestPhoto.file_id}`);
            }
        }
        
        // Add media type for tool context
        if (input.contentSummary.hasMedia && input.contentSummary.mediaType) {
            metadata.push(`MEDIA_TYPE: ${input.contentSummary.mediaType}`);
        }
        
        // Add caption entities if available
        if (input.entities && input.entities.length > 0) {
            const entitiesInfo = input.entities.map(entity => {
                return `${entity.type}:${entity.offset}-${entity.offset + entity.length}${entity.url ? ':' + entity.url : ''}`;
            });
            metadata.push(`CAPTION_ENTITIES: ${entitiesInfo.join(',')}`);
        }
    }
    
    // Fallback: Process raw Telegram data if no contentSummary
    else if (input && input.message) {
        const msg = input.message;
        
        // Extract main content for LLM processing
        if (msg.text) {
            mainContent = msg.text;
        } else if (msg.caption) {
            mainContent = msg.caption;
        }
        
        // Extract media metadata for tool use
        // Priority order: animation > video > photo > document > audio
        // This prevents animated GIFs from being treated as generic documents
        if (msg.animation) {
            metadata.push(`FILE_ID: ${msg.animation.file_id}`);
            metadata.push(`MEDIA_TYPE: animation`);
        } else if (msg.video) {
            metadata.push(`FILE_ID: ${msg.video.file_id}`);
            metadata.push(`MEDIA_TYPE: video`);
        } else if (msg.photo && msg.photo.length > 0) {
            const largestPhoto = msg.photo[msg.photo.length - 1];
            metadata.push(`FILE_ID: ${largestPhoto.file_id}`);
            metadata.push(`MEDIA_TYPE: photo`);
        } else if (msg.document) {
            metadata.push(`FILE_ID: ${msg.document.file_id}`);
            metadata.push(`MEDIA_TYPE: document`);
        } else if (msg.audio) {
            metadata.push(`FILE_ID: ${msg.audio.file_id}`);
            metadata.push(`MEDIA_TYPE: audio`);
        }
        
        // Extract forward metadata for context
        if (msg.forward_origin) {
            const origin = msg.forward_origin;
            if (origin.type === 'channel' && origin.chat) {
                const channelInfo = origin.chat.username
                    ? `@${origin.chat.username}`
                    : origin.chat.title;
                metadata.push(`FORWARDED_FROM: ${channelInfo}`);
            } else if (origin.type === 'user' && origin.sender_user) {
                const userInfo = origin.sender_user.username
                    ? `@${origin.sender_user.username}`
                    : origin.sender_user.first_name;
                metadata.push(`FORWARDED_FROM_USER: ${userInfo}`);
            }
        }

        // Extract caption entities from raw Telegram data with enhanced formatting
        const entities = msg.caption_entities || msg.entities || [];
        if (entities.length > 0) {
            const entitiesInfo = entities.map(entity => {
                let entityStr = `${entity.type}:${entity.offset}-${entity.offset + entity.length}`;

                // Add URL for text_link and url types
                if (entity.url) {
                    entityStr += `:${entity.url}`;
                }

                // Add custom emoji ID for custom_emoji type
                if (entity.custom_emoji_id) {
                    entityStr += `:emoji_id=${entity.custom_emoji_id}`;
                }

                return entityStr;
            });
            metadata.push(`CAPTION_ENTITIES: ${entitiesInfo.join(', ')}`);
        }
    }
    
    // If no content extracted
    if (!mainContent && metadata.length === 0) {
        mainContent = '[No content to repost]';
    }
    
    // Build the final output with clear separation
    let finalOutput = '';
    
    // Add instructions for the AI agent
    finalOutput += '=== INSTRUCTIONS FOR AI AGENT ===\n';
    finalOutput += 'Process the CONTENT section below for reposting. The METADATA section contains technical information for tool use only - DO NOT include metadata in your final text output.\n\n';
    
    // Add main content section
    finalOutput += '=== CONTENT FOR REPOSTING ===\n';
    finalOutput += mainContent || '[No text content]';
    finalOutput += '\n\n';
    
    // Add metadata section if present
    if (metadata.length > 0) {
        finalOutput += '=== METADATA FOR TOOLS (DO NOT INCLUDE IN FINAL TEXT) ===\n';
        finalOutput += metadata.join('\n');
    }
    
    // Return as plain text
    return {
        json: {
            text: finalOutput
        }
    };
});

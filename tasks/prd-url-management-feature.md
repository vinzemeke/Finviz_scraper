# Product Requirements Document: URL Management Feature

## Introduction/Overview

The URL Management Feature enhances the existing Finviz Stock Scraper web application by adding comprehensive CRUD (Create, Read, Update, Delete) operations for saved Finviz URLs. Users can now edit both the name and URL of saved entries, delete URLs with confirmation, and manage their URL collection more effectively.

**Problem Statement:** Currently, users can only add and view saved URLs. There's no way to edit existing entries or remove unwanted URLs, limiting the flexibility of the application.

**Goal:** Provide a complete URL management system that allows users to edit, update, and delete saved Finviz URLs with a user-friendly interface and proper confirmation mechanisms.

## Goals

1. **Edit Functionality:** Allow users to modify both the name and URL of saved entries
2. **Delete Functionality:** Enable users to remove unwanted URLs with confirmation
3. **Visual Indicators:** Provide clear edit and delete buttons for each URL entry
4. **Separate Edit Page:** Create a dedicated page for editing URL details
5. **Data Integrity:** Maintain existing CSV files while updating URL references
6. **User Experience:** Implement confirmation dialogs to prevent accidental deletions

## User Stories

1. **As a user**, I want to edit the name of a saved URL so that I can better organize my Finviz screeners.

2. **As a user**, I want to update the URL of a saved entry so that I can fix typos or update to new filter criteria.

3. **As a user**, I want to delete a saved URL so that I can remove outdated or unused screeners from my list.

4. **As a user**, I want to see clear edit and delete buttons next to each URL so that I can easily identify management actions.

5. **As a user**, I want a confirmation dialog before deleting URLs so that I don't accidentally remove important entries.

6. **As a user**, I want to edit URLs on a separate page so that I have a focused editing experience.

## Functional Requirements

1. **Edit URL Functionality:** The system must allow users to edit both the name and URL of saved entries.

2. **Edit Page Navigation:** The system must provide a dedicated edit page accessible from the main URL list.

3. **Visual Indicators:** The system must display edit and delete icons/buttons next to each URL in the main list.

4. **Form Validation:** The system must validate that edited URLs are valid Finviz screener URLs before saving.

5. **Confirmation Dialog:** The system must show a confirmation dialog before deleting any URL.

6. **Cancel Functionality:** The system must allow users to cancel edit operations without saving changes.

7. **Data Preservation:** The system must preserve existing CSV result files when URLs are edited or deleted.

8. **Error Handling:** The system must handle validation errors and display appropriate error messages.

9. **Success Feedback:** The system must provide clear feedback when edit or delete operations are successful.

## Non-Goals (Out of Scope)

1. **Bulk Operations:** Bulk edit or delete multiple URLs at once
2. **URL History:** Tracking changes to URLs over time
3. **CSV File Management:** Automatic deletion or renaming of CSV result files
4. **Advanced Validation:** Complex URL validation beyond basic Finviz screener format
5. **User Permissions:** Multi-user access control or permission management

## Design Considerations

- **Modal vs Separate Page:** Use a separate edit page for better focus and mobile compatibility
- **Visual Indicators:** Use standard icons (pencil for edit, trash for delete) with hover tooltips
- **Form Layout:** Simple form with name and URL fields, plus Save/Cancel buttons
- **Confirmation Dialog:** Modal dialog with clear messaging about what will be deleted
- **Responsive Design:** Ensure edit page works well on both desktop and mobile devices

## Technical Considerations

- **URL Validation:** Reuse existing Finviz URL validation logic from the scraper module
- **State Management:** Maintain URL list state during edit operations
- **Error Handling:** Implement proper error handling for validation and database operations
- **User Feedback:** Use Flask flash messages for success/error notifications
- **CSV File Handling:** Keep existing CSV files intact, only update URL references in the database

## Success Metrics

1. **Usability:** Users can successfully edit URL names and URLs without errors
2. **Data Integrity:** No loss of existing CSV result files during edit/delete operations
3. **User Experience:** Confirmation dialogs prevent accidental deletions
4. **Validation:** Invalid URLs are caught and appropriate error messages are shown
5. **Performance:** Edit and delete operations complete within 2 seconds

## Open Questions

1. **Character Limits:** Should there be maximum length limits for URL names?
2. **Duplicate Names:** How should the system handle duplicate URL names after editing?
3. **Edit History:** Should we track when URLs were last edited for audit purposes?
4. **Mobile Experience:** Are there any specific mobile UX considerations for the edit page?
5. **Accessibility:** What accessibility features should be included for screen readers?

## Implementation Notes

- Extend the existing URLManager class to support update and delete operations
- Create new Flask routes for edit and delete functionality
- Add JavaScript for confirmation dialogs and form validation
- Update the main page template to include edit/delete buttons
- Ensure proper error handling and user feedback throughout the feature 